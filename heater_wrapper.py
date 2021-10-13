from dataclasses import dataclass
import pathlib
import logging

import config_all

import heater_hsm
from src_micropython.micropython_portable import Thermometrie
from micropython_proxy import HWTYPE_HEATER_THERMOMETRIE_2021
from micropython_interface import MicropythonInterface
from heater_driver_utils import (
    Quantity,
    QuantityNotFoundException,
    EnumLogging,
    EnumHeating,
    EnumExpert,
    EnumThermometrie,
)
from heater_pid_controller import PidController

logger = logging.getLogger("LabberDriver")

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent


@dataclass
class NotInitialized:
    pass


NOT_INITIALIZED = NotInitialized()


class HeaterWrapper:
    def __init__(self, hwserial):
        self.dict_values = {}
        self.mpi = MicropythonInterface(hwserial)
        self.controller = None

        self.insert_config = config_all.ConfigInsert.load_config(
            config_all.ONEWIRE_ID_UNDEFINED
        )
        self.heater_2021_config = config_all.ConfigHeater2021.load_config(
            serial=self.mpi.heater_thermometrie_2021_serial
        )
        logger.info(
            f"{HWTYPE_HEATER_THERMOMETRIE_2021} connected: {self.heater_2021_config}"
        )
        self.dict_values[Quantity.StatusReadSerialNumberHeater] = repr(
            self.heater_2021_config
        )

        self.hsm_heater = heater_hsm.HeaterHsm(self)
        # self.hsm_defrost = heater_hsm.DefrostHsm(self)

        self.filename_values = (
            DIRECTORY_OF_THIS_FILE
            / f"Values-{self.mpi.heater_thermometrie_2021_serial}.txt"
        )

        def init_hsm(hsm):
            def log_main(msg):
                logger.debug(f"*** {msg}")

            def log_sub(msg):
                logger.debug(f"     {msg}")

            def log_state_change(signal, handling_state, state_before, new_state):
                logger.info(f"{repr(signal)}")
                logger.info(f"  {handling_state}: {state_before} -> {new_state}")

            hsm.func_log_main = log_main
            hsm.func_log_sub = log_sub
            hsm.func_state_change = log_state_change
            hsm.reset()

        init_hsm(self.hsm_heater)
        # init_hsm(self.hsm_defrost, "defrost")

        self.mpi.init()

        id_box = self.mpi.onewire_box.scan()
        id_box_expected = self.heater_2021_config.ONEWIRE_ID_HEATER
        if id_box != id_box_expected:
            logger.warning(
                f"Expected onewire_id of heater '{id_box_expected}' but got '{id_box}"
            )

        # Read all initial values from the pyboard
        self.dict_values[Quantity.ControlWriteHeating] = EnumHeating.OFF
        self.dict_values[Quantity.ControlWriteTemperature] = 0.0
        self.dict_values[Quantity.TemperatureReadonlyTemperatureCalibrated] = 0.0
        self.tick()

    def close(self):
        self.mpi.close()

    @property
    def time_now_s(self) -> float:
        return self.mpi.timebase.now_s

    def sleep(self, duration_s: float) -> None:
        self.mpi.timebase.sleep(duration_s=duration_s)

    def tick(self) -> float:
        self.mpi.fe.sim_update_time(time_now_s=self.time_now_s)

        self._tick_read_from_pyboard()

        self._tick_read_onewire()

        self._tick_run_controller()

        # Run statemachine
        self.hsm_heater.dispatch(heater_hsm.SIGNAL_TICK)
        return self.mpi.timebase.now_s

    def _tick_read_from_pyboard(self):
        for carbon, label, current_factor in (
            (True, "carbon", Thermometrie.CURRENT_A_CARBON),
            (False, "PT1000", Thermometrie.CURRENT_A_PT1000),
        ):
            temperature_V = self.mpi.temperature_insert.get_voltage(carbon=carbon)
            temperature_R = temperature_V / current_factor
            # print(
            #     f"{label}: {temperature_V:0.3f} V, {temperature_R:0.3f} Ohm"
            # )
            # TODO: Calibration table
            temperature_K = temperature_V
            quantity = Quantity.TemperatureReadonlyResistanceCarbon if carbon else Quantity.TemperatureReadonlyResistancePT1000_K
            self.dict_values[quantity] = temperature_R
            quantity = Quantity.TemperatureReadonlyTemperatureCarbon if carbon else Quantity.TemperatureReadonlyTemperaturePT1000_K
            self.dict_values[quantity] = temperature_K
            if carbon:
                self.dict_values[Quantity.TemperatureReadonlyTemperatureCalibrated] = temperature_K

        def defrost_switch_changed(on: str) -> str:
            self.hsm_heater.dispatch(heater_hsm.SignalDefrostSwitchChanged(on=on))
            return on

        self._set_value(
            Quantity.StatusReadDefrostSwitchOnBox,
            self.mpi.defrost_switch.is_on(),
            defrost_switch_changed,
        )

    def _tick_read_onewire(self):
        def insert_onewire_id_changed(onewire_id: str) -> str:
            self.hsm_heater.dispatch(
                heater_hsm.SignalInsertSerialChanged(serial=onewire_id)
            )
            self.insert_config = config_all.ConfigInsert.load_config(
                onewire_id=onewire_id
            )
            self.dict_values[Quantity.StatusReadSerialNumberInsert] = repr(
                self.insert_config
            )
            return onewire_id

        self.mpi.onewire_insert.set_power(on=True)
        self._set_value(
            Quantity.StatusReadSerialNumberInsertHidden,
            self.mpi.onewire_insert.scan(),
            insert_onewire_id_changed,
        )
        self.mpi.onewire_insert.set_power(on=False)

    def _tick_run_controller(self):
        if self.controller is not None:
            temperature_calibrated_K = self.dict_values[
                    Quantity.TemperatureReadonlyTemperatureCalibrated
                ]
            self.controller.process(
                time_now_s=self.mpi.timebase.now_s,
                fSetpoint=self.dict_values[Quantity.ControlWriteTemperature],
                fSensorValue=temperature_calibrated_K,
                fLimitOutLow=0.0,
                fLimitOutHigh=100.0,
            )
            power = int(self.controller.fOutputValueLimited)
            power = max(0, min(100, power))
            self.dict_values[
                Quantity.ControlWritePower
            ] = power
            self.mpi.fe.proxy.heater.set_power(power)

            logger.info(f"  setpoint={self.controller.fSetpoint:0.2f} K => power={self.controller.fOutputValueLimited:0.2f} % => temperature_calibrated_K={temperature_calibrated_K:0.2f}")

    def get_quantity(self, quantity: Quantity):
        assert isinstance(quantity, Quantity)
        return self.get_value(quantity.value)

    def get_value(self, name: str):
        assert isinstance(name, str)
        quantity = Quantity(name)
        if quantity == Quantity.ControlWriteThermometrie:
            return self.hsm_heater.get_labber_thermometrie
        if quantity == Quantity.StatusReadInsertConnected:
            return self.hsm_heater.get_labber_insert_connected

        if quantity == Quantity.ControlWriteTemperatureAndWait:
            # TemperatureAndWait is stored as Temperature
            quantity = Quantity.ControlWriteTemperature

        try:
            return self.dict_values[quantity]
        except KeyError as e:
            raise QuantityNotFoundException(name) from e

    def set_value(self, name: str, value):
        assert isinstance(name, str)
        self.set_quantity(quantity=Quantity(name), value=value)

    def set_quantity(self, quantity: Quantity, value):
        assert isinstance(quantity, Quantity)
        if quantity == Quantity.ControlWriteHeating:
            value_new = EnumHeating(value)
            self.hsm_heater.dispatch(heater_hsm.SignalHeating(value=value_new))
            return value
        if quantity == Quantity.ControlWriteExpert:
            value_new = EnumExpert(value)
            self.dict_values[quantity] = value_new
            return value
        if quantity == Quantity.ControlWriteLogging:
            value_new = EnumLogging(value)
            self.dict_values[quantity] = value_new
            value_new.setLevel()
            return value
        if quantity == Quantity.ControlWriteThermometrie:
            value_new = EnumThermometrie(value)
            self.hsm_heater.dispatch(heater_hsm.SignalThermometrie(value=value_new))
            return value
        if quantity == Quantity.ControlWriteGreenLED:
            value_new = bool(value)
            self.dict_values[quantity] = value_new
            return value
        if quantity in (
            Quantity.ControlWriteTemperature,
            Quantity.ControlWriteTemperatureAndWait,
        ):
            # This is the same temperature
            self.dict_values[Quantity.ControlWriteTemperature] = value
            self.controller = PidController(
                "insert",
                time_now_s=self.mpi.timebase.now_s,
                fSetpoint=self.dict_values[Quantity.ControlWriteTemperature],
                fKi=0.4,
                fKp=1.0,
                fKd=0.0
            )
            return value

        if quantity in (
            Quantity.ControlWritePower,
            Quantity.ControlWriteTemperatureBox,
            Quantity.ControlWriteTemperatureToleranceBand,
            Quantity.ControlWriteSettleTime,
            Quantity.ControlWriteTimeoutTime,
        ):
            self.dict_values[quantity] = value
            return value
        raise QuantityNotFoundException(quantity.name)

    def _set_value(self, quantity: Quantity, value, func=None) -> bool:
        """
        Returns true if value changes
        """
        before = self.dict_values.get(quantity, NOT_INITIALIZED)
        after = self.dict_values[quantity] = value
        value_changed = before != after
        if value_changed and func is not None:
            func(value)
        return value_changed

    def signal(self, signal):
        self.hsm_heater.dispatch(signal)

    def expect_state(self, expected_meth):
        self.hsm_heater.expect_state(expected_meth=expected_meth)
