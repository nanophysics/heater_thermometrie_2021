from dataclasses import dataclass
import pathlib
import logging
import importlib

import config_all

import heater_hsm
from pytest_util import AssertDisplay
from micropython_proxy import HWTYPE_HEATER_THERMOMETRIE_2021
from micropython_interface import MicropythonInterface, TICK_INTERVAL_S
from heater_driver_utils import (
    Quantity,
    QuantityNotFoundException,
    EnumLogging,
    EnumHeating,
    EnumExpert,
    EnumThermometrie,
)

logger = logging.getLogger("LabberDriver")

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent


TEMPERATURE_SETTLE_K = -1.0


@dataclass
class NotInitialized:
    pass


NOT_INITIALIZED = NotInitialized()


class ErrorCounterAssertion:
    def __init__(self, ht: "HeaterWrapper"):
        assert isinstance(ht, HeaterWrapper)
        self._ht = ht
        self._error_counter = self._ht.hsm_heater.error_counter

    def assert_errors(self):
        error_counter = self._ht.hsm_heater.error_counter
        assert error_counter > self._error_counter
        self._error_counter = error_counter

    def assert_no_errors(self):
        error_counter = self._ht.hsm_heater.error_counter
        assert error_counter == self._error_counter

    def reset(self):
        self._error_counter = self._ht.hsm_heater.error_counter


class HeaterWrapper:
    def __init__(self, hwserial, force_use_realtime_factor: float = None):
        self.dict_values = {}
        self.mpi = MicropythonInterface(hwserial, force_use_realtime_factor=force_use_realtime_factor)
        self.tick_count = 0

        self.heater_2021_config = config_all.ConfigHeater2021.load_config(serial=self.mpi.heater_thermometrie_2021_serial)
        logger.info(f"{HWTYPE_HEATER_THERMOMETRIE_2021} connected: {self.heater_2021_config}")
        self.dict_values[Quantity.StatusReadSerialNumberHeater] = repr(self.heater_2021_config)
        self.insert_config = None
        self.insert_calibration = None
        self.insert_connected(onewire_id=config_all.ONEWIRE_ID_INSERT_UNDEFINED)

        self.hsm_heater = heater_hsm.HeaterHsm(self)

        self.filename_values = DIRECTORY_OF_THIS_FILE / f"Values-{self.mpi.heater_thermometrie_2021_serial}.txt"

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
            logger.warning(f"Expected onewire_id of heater '{id_box_expected}' but got '{id_box}")

        # Read all initial values from the pyboard
        self.dict_values[Quantity.ControlWriteThermometrie] = EnumThermometrie.OFF
        self.dict_values[Quantity.ControlWriteHeating] = EnumHeating.OFF
        self.dict_values[Quantity.ControlWriteTemperature] = 0.0
        self.dict_values[Quantity.ControlWriteTemperatureToleranceBand] = 1.0
        self.dict_values[Quantity.ControlWriteSettleTime] = 10.0
        self.dict_values[Quantity.ControlWriteTimeoutTime] = 20.0
        self.dict_values[Quantity.TemperatureReadonlyTemperatureCalibrated_K] = TEMPERATURE_SETTLE_K
        self.dict_values[Quantity.StatusReadErrorCounter] = 0
        self.tick()

    def close(self):
        self.mpi.close()

    def insert_connected(self, onewire_id: str):
        assert isinstance(onewire_id, str)
        self.insert_config = config_all.ConfigInsert.load_config(onewire_id)
        modulename = f"calibration.tail_{self.insert_config.HWSERIAL}"
        try:
            self.insert_calibration = importlib.import_module(modulename)
        except ModuleNotFoundError as e:
            msg = f"Calibration module '{modulename}' not found!"
            print(f"ERROR: {msg}")
            logger.warning(msg)
        except Exception as e:
            msg = f"Error in '{modulename}': {repr(e)}"
            print(f"ERROR: {msg}")
            logger.exception(e)
            raise

    @property
    def time_now_s(self) -> float:
        return self.mpi.timebase.now_s

    def sleep(self, duration_s: float) -> None:
        self.mpi.timebase.sleep(duration_s=duration_s)

    def let_time_fly(self, duration_s: float = None, till_s: float = None):
        assert isinstance(duration_s, (type(None), float))
        assert isinstance(till_s, (type(None), float))

        if (duration_s is not None) and (till_s is not None):
            raise AttributeError()

        if duration_s is not None:
            till_s = self.time_now_s + duration_s

        next_tick_s = time_s = self.time_now_s
        while True:
            next_tick_s += TICK_INTERVAL_S
            self.sleep(duration_s=next_tick_s - time_s)
            time_s = self.tick()

            if till_s is None:
                # Loop forever
                continue

            if time_s >= till_s - 1e-9:
                return

    def tick(self) -> float:
        self.mpi.sim_update_time(time_now_s=self.time_now_s)

        self._tick_read_from_pyboard()

        self._tick_read_onewire()

        # Run statemachine
        self.hsm_heater.assert_valid_state()
        self.hsm_heater.dispatch(heater_hsm.SIGNAL_TICK)
        self.hsm_heater.assert_valid_state()

        # Update display
        self._tick_update_display()
        self.tick_count += 1
        return self.mpi.timebase.now_s

    def _tick_read_from_pyboard(self):
        #
        # Read carbon and pt1000 and calculate calibrated temperature
        #
        def read(carbon, quantity):
            resistance_OHM = self.mpi.temperature_insert.read_resistance_OHM(carbon=carbon)
            self.dict_values[quantity] = resistance_OHM
            return resistance_OHM

        Calibration = self.insert_calibration.Calibration
        calibration = Calibration(
            carbon_OHM=read(True, Quantity.TemperatureReadonlyResistanceCarbon_OHM),
            pt1000_OHM=read(False, Quantity.TemperatureReadonlyResistancePT1000_OHM),
        )

        self.dict_values[Quantity.TemperatureReadonlyTemperatureCarbon_K] = calibration.carbon_K
        self.dict_values[Quantity.TemperatureReadonlyTemperaturePT1000_K] = calibration.pt1000_K
        self.dict_values[Quantity.TemperatureReadonlyTemperatureCalibrated_K] = calibration.calibrated_K

        def defrost_switch_changed(defrost_on: str) -> str:
            self.hsm_heater.dispatch(heater_hsm.SignalDefrostSwitchChanged(defrost_on=defrost_on))
            return defrost_on

        self._set_value(
            Quantity.StatusReadDefrostSwitchOnBox,
            self.mpi.defrost_switch.is_on(),
            defrost_switch_changed,
        )

    def _tick_read_onewire(self):
        def insert_onewire_id_changed(onewire_id: str) -> str:
            self.hsm_heater.dispatch(heater_hsm.SignalInsertSerialChanged(onewire_id=onewire_id))
            self.insert_connected(onewire_id=onewire_id)
            self.dict_values[Quantity.StatusReadSerialNumberInsert] = repr(self.insert_config)
            return onewire_id

        self._set_value(
            Quantity.StatusReadSerialNumberInsertHidden,
            self.mpi.onewire_insert.scan(),
            insert_onewire_id_changed,
        )

    def _tick_update_display(self):
        display = self.mpi.display
        display.clear()
        temperature_calibrated_K = self.get_quantity(Quantity.TemperatureReadonlyTemperatureCalibrated_K)
        display.line(0, f" {temperature_calibrated_K:>13.1f}K")
        status = {
            heater_hsm.HeaterHsm.state_disconnected: " DISCONNECTED",
            heater_hsm.HeaterHsm.state_connected_thermoff: " THERMOFF",
            heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled: " HEATING\n CONTROLLED",
            heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual: " HEATING\n MANUAL",
            heater_hsm.HeaterHsm.state_connected_thermon_heatingoff: " HEATING\n OFF",
            heater_hsm.HeaterHsm.state_connected_thermon_defrost: " DEFROST",
        }.get(self.hsm_heater.actual_meth(), "?")
        status1, _, status2 = status.partition("\n")
        display.line(1, status1)
        display.line(2, status2)

        # is_in_range = self.hsm_heater.is_in_range()
        # settled_duration_s = self.hsm_heater.settled_duration_s
        error_counter = self.get_quantity(Quantity.StatusReadErrorCounter)
        # settled = self.get_quantity(Quantity.StatusReadSettled)
        # timeout = self.get_quantity(Quantity.StatusReadTimout)

        if self.hsm_heater.is_outofrange():
            text = " out of range"
        else:
            text = f" in range {self.hsm_heater.duration_inrange_s():0.0f}s"
        display.line(3, text)
        display.line(4, f" errors {error_counter}")

        display.show_lines()

    def get_quantity(self, quantity: Quantity):
        assert isinstance(quantity, Quantity)
        # if quantity == Quantity.ControlWriteThermometrie:
        #     return self.hsm_heater.get_labber_thermometrie
        if quantity == Quantity.StatusReadInsertConnected:
            return self.hsm_heater.get_labber_insert_connected
        if quantity == Quantity.StatusReadSettled:
            return self.hsm_heater.is_settled()
        if quantity == Quantity.StatusReadErrorCounter:
            return self.hsm_heater.error_counter
        if quantity == Quantity.ControlWriteTemperatureAndSettle:
            return TEMPERATURE_SETTLE_K
        try:
            return self.dict_values[quantity]
        except KeyError as e:
            raise QuantityNotFoundException(quantity.name) from e

    def get_value(self, name: str):
        assert isinstance(name, str)
        self.get_quantity(quantity=Quantity(name))

    def set_value(self, name: str, value):
        assert isinstance(name, str)
        return self.set_quantity(quantity=Quantity(name), value=value)

    def set_quantity(self, quantity: Quantity, value):
        assert isinstance(quantity, Quantity)
        if quantity == Quantity.ControlWriteHeating:
            value_new = EnumHeating(value)
            # self.hsm_heater.dispatch(heater_hsm.SignalHeating(value=value_new))
            self.dict_values[quantity] = value_new
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
            # self.hsm_heater.dispatch(heater_hsm.SignalThermometrie(value=value_new))
            self.dict_values[quantity] = value_new
            return value
        if quantity == Quantity.ControlWriteGreenLED:
            value_new = bool(value)
            self.dict_values[quantity] = value_new
            return value
        if quantity == Quantity.ControlWriteTemperatureAndSettle:
            self.set_quantity(Quantity.ControlWriteTemperature, value)
            return TEMPERATURE_SETTLE_K

        if quantity == Quantity.ControlWritePower100:
            if not (0.0 <= value <= 100.0):
                logger.warning(f"Expected power to be between 0 and 100, but got {value:0.3f}.")
            power_dac = int(2 ** 16 * value / 100.0)
            power_dac = max(0, min(2 ** 16 - 1, power_dac))
            self.mpi.heater.set_power(power=power_dac)
            self.dict_values[quantity] = value
            return value

        if quantity in (
            Quantity.ControlWriteTemperature,
            Quantity.TemperatureReadonlyTemperatureBox,
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

    @property
    def error_counter_assertion(self):
        return ErrorCounterAssertion(ht=self)

    def signal(self, signal):
        self.hsm_heater.dispatch(signal)

    def expect_state(self, expected_meth):
        self.hsm_heater.expect_state(expected_meth=expected_meth)

    def expect_display(self, readable_expected):
        self._tick_update_display()
        lines = self.mpi.display.sim_get
        AssertDisplay.assert_equal(lines=lines, readable_expected=readable_expected)

    def sim_reset_error_counter(self):
        self.hsm_heater.sim_reset_error_counter()
