from dataclasses import dataclass
import pathlib
import logging
import importlib

import config_all

import heater_hsm
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
from heater_heatingrate import HeatingCurve

logger = logging.getLogger("LabberDriver")

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent


TEMPERATURE_SETTLE_OFF_K = -1.0
TEMPERATURE_BOX_UNDEFINED_C = -1.0
INTERVAL_READ_BOXTEMP_S = 30 # To read the box temperature takes 0.8s, therefore we do not read it every time

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
        self.heatingrate = HeatingCurve(heating_power_max_W=heater_hsm.HEATING_POWER_MAX_W)
        self.tick_count = 0
        self.tick_count_next_boxtemp = 0
        self.dict_values = {}
        self.mpi = MicropythonInterface(hwserial, force_use_realtime_factor=force_use_realtime_factor)

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
        self.dict_values[Quantity.ControlWritePower_W] = 0.0
        self.dict_values[Quantity.ControlWriteThermometrie] = EnumThermometrie.OFF
        self.dict_values[Quantity.ControlWriteHeating] = EnumHeating.OFF
        self.dict_values[Quantity.ControlWriteTemperature_K] = 0.0
        self.dict_values[Quantity.ControlWriteTemperatureToleranceBand_K] = 1.0
        self.dict_values[Quantity.ControlWriteSettleTime_S] = 10.0
        self.dict_values[Quantity.ControlWriteTimeoutTime_S] = 20.0
        self.dict_values[Quantity.TemperatureReadonlyTemperatureCalibrated_K] = TEMPERATURE_SETTLE_OFF_K
        self.dict_values[Quantity.StatusReadErrorCounter] = 0
        self.dict_values[Quantity.StatusReadTemperatureBox_C] = TEMPERATURE_BOX_UNDEFINED_C
        self.dict_values[Quantity.ControlWriteLogging] = EnumLogging.WARNING

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

        self._tick_read_onewire_boxtemp()

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
            measured_OHM = self.mpi.temperature_insert.read_resistance_OHM(carbon=carbon)
            calibrated_OHM = self.heater_2021_config.calibrate_resistance_OHM(carbon=carbon, measured_OHM=measured_OHM)
            self.dict_values[quantity] = calibrated_OHM
            return calibrated_OHM

        Calibration = self.insert_calibration.Calibration
        calibration = Calibration(
            carbon_OHM=read(True, Quantity.TemperatureReadonlyResistanceCarbon_OHM),
            pt1000_OHM=read(False, Quantity.TemperatureReadonlyResistancePT1000_OHM),
        )

        self.dict_values[Quantity.TemperatureReadonlyTemperatureCarbon_K] = calibration.carbon_K
        self.dict_values[Quantity.TemperatureReadonlyTemperaturePT1000_K] = calibration.pt1000_K
        self.dict_values[Quantity.TemperatureReadonlyTemperatureCalibrated_K] = calibration.calibrated_K

        actual_meth = self.hsm_heater.actual_meth()
        if actual_meth != heater_hsm.HeaterHsm.state_disconnected:
            overhead_protection_C = 70.0
            if calibration.pt1000_K > overhead_protection_C + 273.15:
                # Overheat protection
                # Power off bei Temperatur > 70C(343.15K).
                logger.warning(f"Overheat protection {overhead_protection_C}C. Switch power off!")
                self.set_power_W(power_W=0.0)

        def defrost_switch_changed(defrost_on: str) -> str:
            self.hsm_heater.dispatch(heater_hsm.SignalDefrostSwitchChanged(defrost_on=defrost_on))
            return defrost_on

        self._set_value(
            Quantity.StatusReadDefrostSwitchOnBox,
            self.mpi.defrost_switch.is_on(),
            defrost_switch_changed,
        )

    def _tick_read_onewire(self):
        actual_meth = self.hsm_heater.actual_meth()
        if actual_meth != heater_hsm.HeaterHsm.state_disconnected:
            # The tail has been connected and OneWireID was read.
            # Now the statemachine will poll the PTC1000 to detect
            # the disconnection of the tail.
            return

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

    def _tick_read_onewire_boxtemp(self):
        if self.hsm_heater.is_state_or_substate(heater_hsm.HeaterHsm.state_connected_thermon):
            if self.tick_count < self.tick_count_next_boxtemp:
                return
            self.tick_count_next_boxtemp = self.tick_count + INTERVAL_READ_BOXTEMP_S // TICK_INTERVAL_S
            onewire_id = self.heater_2021_config.ONEWIRE_ID_HEATER
            if onewire_id != config_all.ONEWIRE_ID_HEATER_UNDEFINED:
                box_temp_c = self.mpi.onewire_box.read_temp_C(ident=onewire_id)
                self.dict_values[Quantity.StatusReadTemperatureBox_C] = box_temp_c
                return

        self.dict_values[Quantity.StatusReadTemperatureBox_C] = TEMPERATURE_BOX_UNDEFINED_C

    def _tick_update_display(self):
        display = self.mpi.display
        display.clear()
        temperature_K = self.get_quantity(Quantity.TemperatureReadonlyTemperatureCalibrated_K)
        display.line(0, f" {temperature_K:>13.1f}K")
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

        error_counter = self.get_quantity(Quantity.StatusReadErrorCounter)

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
        if quantity == Quantity.StatusReadDefrostUserInteraction:
            return "?"
        if quantity == Quantity.StatusReadInsertConnected:
            return self.hsm_heater.get_labber_insert_connected
        if quantity == Quantity.StatusReadSettled:
            return self.hsm_heater.is_settled()
        if quantity == Quantity.StatusReadErrorCounter:
            return self.hsm_heater.error_counter
        if quantity == Quantity.ControlWriteTemperatureAndSettle_K:
            return TEMPERATURE_SETTLE_OFF_K
        try:
            # Verify if all keys are of enum 'Quantity'
            for q in self.dict_values.keys():
                assert isinstance(q, Quantity), f"{q}`is not a enum Quantity"
            if 1 < 0:
                logger.info("*" * 100)
                for q in sorted(self.dict_values.keys(), key=lambda q: q.name):
                    logger.info(f"   {q} -> {self.dict_values[q]}")
            return self.dict_values[quantity]
        except KeyError as e:
            raise QuantityNotFoundException(quantity.name) from e

    def get_value(self, name: str):
        assert isinstance(name, str)
        return self.get_quantity(quantity=Quantity(name))

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
        if quantity == Quantity.ControlWriteTemperature_K:
            difference_K = abs(value - self.dict_values[quantity])
            if difference_K > 1e-9:
                # settle and timeout must start from zero
                self.hsm_heater.reset_outofrange_s()
            self.dict_values[quantity] = value
            return value
        if quantity == Quantity.ControlWriteTemperatureAndSettle_K:
            self.set_quantity(Quantity.ControlWriteTemperature_K, value)
            return TEMPERATURE_SETTLE_OFF_K

        if quantity == Quantity.ControlWritePower_W:
            actual_meth = self.hsm_heater.actual_meth()
            if actual_meth != heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual:
                logger.warning(f"The power may only controlled in mode MANUAL. Actual mode '{actual_meth.__name__}'")
                return 0.0

            return self.set_power_W(power_W=value)

        if quantity in (
            Quantity.ControlWriteTemperatureToleranceBand_K,
            Quantity.ControlWriteSettleTime_S,
            Quantity.ControlWriteTimeoutTime_S,
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
        from pytest_util import AssertDisplay

        AssertDisplay.assert_equal(lines=lines, readable_expected=readable_expected)

    def sim_reset_error_counter(self):
        self.hsm_heater.sim_reset_error_counter()

    def set_power_W(self, power_W: float):
        """
        Limit power.
        Set labber relevant variable.
        Set power in the pyboard.
        """
        assert isinstance(power_W, float)
        if not (0.0 <= power_W <= heater_hsm.HEATING_POWER_MAX_W):
            logger.warning(f"Expected power to be between 0 and {heater_hsm.HEATING_POWER_MAX_W:0.3f} W, but got {power_W:0.3f}.")
            power_W = max(0.0, min(heater_hsm.HEATING_POWER_MAX_W, power_W))
        self.dict_values[Quantity.ControlWritePower_W] = power_W

        power_dac = self.heatingrate.get_DAC(power_W=power_W)
        self.mpi.heater.set_power(power=power_dac)

        return power_W
