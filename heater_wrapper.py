import os
import sys
import re
import enum
import math
import time
import pathlib
import logging

import config_all
import calib_prepare_lib

from micropython_proxy import mp, MicropythonInterface

logger = logging.getLogger("heater_thermometrie_2012")

logger.setLevel(logging.DEBUG)

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent


class QuantityNotFoundException(Exception):
    pass


class EnumMixin:
    @classmethod
    def all_text(cls):
        return ", ".join(sorted([f'"{d.name}"' for d in cls]))

    @classmethod
    def get_exception(cls, configuration: str, value: str):
        assert isinstance(configuration, str)
        assert isinstance(value, str)
        err = f'{configuration}: Unkown "{value}". Expect one of {cls.all_text()}!'
        try:
            return cls[value]
        except KeyError as e:
            raise Exception(err) from e


class EnumControlHeating(EnumMixin, enum.Enum):
    OFF = "off"
    MANUAL = "manual"
    CONTROLLED = "controlled"


class EnumControlExpert(EnumMixin, enum.Enum):
    SIMPLE = "simple"
    EXPERT = "expert"


class EnumControlThermometrie(EnumMixin, enum.Enum):
    ON = "on"
    OFF = "off"


class Quantity(EnumMixin, enum.Enum):
    """
    Readable name => value as in 'heater_thermometrie_2021.ini'
    """

    Heating = "Heating"
    Expert = "Expert"
    Thermometrie = "Thermometrie"
    GreenLED = "Green LED"
    Power = "power"
    Temperature = "temperature"
    TemperatureBox = "Temperature Box"
    TemperatureToleranceBand = "temperature tolerance band"
    SettleTime = "settle time"
    TimeoutTime = "timeout time"
    SerialNumberHeater = "Serial Number Heater"
    DefrostSwitchOnBox = "Defrost - Switch on box"
    DefrostUserInteraction = "Defrost - User interaction"


class HeaterWrapper:
    def __init__(self, hwserial):
        self.dict_values = {}
        self.mxy = MicropythonInterface(hwserial)

        self.__calibrationLookup = None
        self.ignore_str_dac12 = False
        self.f_write_file_time_s = 0.0
        self.filename_values = DIRECTORY_OF_THIS_FILE / f"Values-{self.mxy.heater_thermometrie_2021_serial}.txt"

        # The time when the dac was set last.
        self.f_last_dac_set_s = 0.0

        # if the driver is not working anymore
        self.b_pyboard_error = False
        self.i_pyboard_geophone_dac = 0
        self.f_pyboard_geophone_read_s = 0

        self.mxy.init()

        return
        self.sync_status_get()

        self.load_calibration_lookup()

    def close(self):
        self.mxy.close()

    def load_calibration_lookup(self):
        if self.heater_thermometrie_2021_serial is None:
            return
        calib_correction_data = calib_prepare_lib.CalibCorrectionData(self.heater_thermometrie_2021_serial)
        self.__calibrationLookup = calib_correction_data.load()

    def reset_calibration_lookup(self):
        self.__calibrationLookup = None

    def tick(self):
        self.dict_values[Quantity.Temperature] = self.mxy.temperature_tail.get_voltage(carbon=True)
        self.dict_values[Quantity.Temperature] = self.mxy.temperature_tail.get_voltage(carbon=False)
        self.dict_values[Quantity.DefrostSwitchOnBox] = self.mxy.get_defrost()
        self.dict_values[Quantity.SerialNumberHeater] = self.mxy.heater_thermometrie_2021_serial
        self.dict_values[Quantity.Power] = 0.53
        self.dict_values[Quantity.Thermometrie] = True

    def set_value(self, name: str, value):
        quantity = Quantity(name)
        # comboboxes = {
        #     Quantity.Heating: EnumControlHeating,
        #     Quantity.Expert: EnumControlExpert,
        #     Quantity.Thermometrie: EnumControlThermometrie,
        #     Quantity.GreenLED: bool,
        # }
        # try:
        #     combobox_class = comboboxes[quantity]
        # except KeyError:
        #     pass
        # else:
        #     value_enum = combobox_class(value)
        #     print(f"set_control_heating({value_new})")
        #     self.dict_values[quantity] = value_enum
        #     return value

        if quantity == Quantity.Heating:
            value_new = EnumControlHeating(value)
            self.dict_values[quantity] = value_new
            return value
        if quantity == Quantity.Expert:
            value_new = EnumControlExpert(value)
            self.dict_values[quantity] = value_new
            return value
        if quantity == Quantity.Thermometrie:
            value_new = EnumControlThermometrie(value)
            self.dict_values[quantity] = value_new
            return value
        if quantity == Quantity.GreenLED:
            value_new = bool(value)
            self.dict_values[quantity] = value_new
            return value
        if quantity in (
            Quantity.Power,
            Quantity.Temperature,
            Quantity.TemperatureBox,
            Quantity.TemperatureToleranceBand,
            Quantity.SettleTime,
            Quantity.TimeoutTime,
        ):
            self.dict_values[quantity] = value
            return value
        raise QuantityNotFoundException(name)

    def get_value(self, name: str):
        quantity = Quantity(name)
        try:
            return self.dict_values.get(quantity, None)
        except KeyboardInterrupt:
            raise QuantityNotFoundException(name)

    def get_dac(self, index):
        """
        Returns the current Voltage
        """
        assert 0 <= index < DACS_COUNT
        return self.list_dacs[index].f_value_V

    def __calculate_and_set_new_dac(self, dict_requested_values):
        """
        Will set the new dac-values:
        self.list_dacs[index].f_value_V = ...
        returns b_done, b_need_wait_before_DAC_set
        """
        b_done = True
        b_need_wait_before_DAC_set = False
        dict_changed_values = {}

        for index, d in dict_requested_values.items():
            assert 0 <= index < DACS_COUNT
            obj_Dac = self.list_dacs[index]
            f_DA_OUT_desired_V = d["f_DA_OUT_desired_V"]
            f_gain = d.get("f_gain", 1.0)
            f_DA_OUT_sweep_VperSecond = d.get("f_DA_OUT_sweep_VperSecond", 0.0)

            def get_actual_DA_OUT_V():
                return obj_Dac.f_value_V * f_gain

            def set_new_DA_OUT_V(f_value_v):
                # Will set the value and update the dict
                obj_Dac.f_value_V = f_value_v / f_gain
                if obj_Dac.f_value_V > VALUE_PLUS_MIN_MAX_V:
                    obj_Dac.f_value_V = VALUE_PLUS_MIN_MAX_V
                if obj_Dac.f_value_V < -VALUE_PLUS_MIN_MAX_V:
                    obj_Dac.f_value_V = -VALUE_PLUS_MIN_MAX_V
                obj_Dac.f_gain = f_gain
                dict_changed_values[index] = f_value_v

            if math.isclose(0.0, f_DA_OUT_sweep_VperSecond):
                # No sweeping
                if not math.isclose(f_DA_OUT_desired_V, get_actual_DA_OUT_V()):
                    set_new_DA_OUT_V(f_DA_OUT_desired_V)
                continue

            # Sweeping requested
            assert f_DA_OUT_sweep_VperSecond >= 0.0
            f_desired_step_V = f_DA_OUT_desired_V - get_actual_DA_OUT_V()
            if math.isclose(0.0, f_desired_step_V):
                # We are on the requested voltage. Nothing to do
                continue

            # We need to sweep
            b_need_wait_before_DAC_set = True
            f_possible_step = F_SWEEPINTERVAL_S * f_DA_OUT_sweep_VperSecond
            if abs(f_desired_step_V) < f_possible_step:
                # We can set the final voltage
                set_new_DA_OUT_V(f_DA_OUT_desired_V)
                continue

            # The sweep rate is limiting
            b_done = False
            f_step_V = math.copysign(f_possible_step, f_desired_step_V)
            set_new_DA_OUT_V(get_actual_DA_OUT_V() + f_step_V)

        return b_done, b_need_wait_before_DAC_set, dict_changed_values

    def sync_dac_set_all(self, dict_requested_values):
        """
        dict_requested_values = {
            0: # Optional. The DAC [0..9]
                {
                    'f_DA_OUT_desired_V': 5.5, # The value to set
                    'f_DA_OUT_sweep_VperSecond': 0.1, # Optional
                    'f_gain': 0.5, # Optional. f_DA_OUT_desired_V=f_dac_desired_V*f_gain
                }
        }

        return: b_done, {
            0: 5.1, # Actual value DA_OUT
        }

        This method will receive try to set the values of the dacs.
        If the call is following very shortly after the last call, it may delay before setting the DACs.
        If required, f_DA_OUT_sweep_VperSecond will be used for small voltage increments.
        The effective set values will be returned. To be used for updateing the display and the log output.
        If b_done == False, the labber driver muss call this method again with the same parameters.
        """
        (
            b_done,
            b_need_wait_before_DAC_set,
            dict_changed_values,
        ) = self.__calculate_and_set_new_dac(dict_requested_values)

        if b_need_wait_before_DAC_set:
            # We have to make sure, that the last call was not closer than F_SWEEPINTERVAL_S
            OVERHEAD_TIME_SLEEP_S = 0.001
            time_to_sleep_s = F_SWEEPINTERVAL_S - (time.perf_counter() - self.f_last_dac_set_s) - OVERHEAD_TIME_SLEEP_S
            if time_to_sleep_s > 0.001:  # It doesn't make sense for the operarting system to stop for less than 1ms
                assert time_to_sleep_s <= F_SWEEPINTERVAL_S
                time.sleep(time_to_sleep_s)

        # Now set the new values to the DACs
        self.f_last_dac_set_s = time.perf_counter()
        self.__sync_dac_set()

        return b_done, dict_changed_values

    def __sync_dac_set(self):
        """
        Send to new dac values to the pyboard.
        Return pyboard_status.
        """
        f_values_plus_min_v = list(map(lambda obj_Dac: obj_Dac.f_value_V, self.list_dacs))
        str_dac20, str_dac12 = compact_2012_dac.getDAC20DAC12HexStringFromValues(f_values_plus_min_v, calibrationLookup=self.__calibrationLookup)
        if self.ignore_str_dac12:
            str_dac12 = "0" * DACS_COUNT * DAC12_NIBBLES
        s_py_command = 'micropython_logic.set_dac("{}", "{}")'.format(str_dac20, str_dac12)
        self.obj_time_span_set_dac.start()

        str_status = self.fe.eval(s_py_command)

        self.obj_time_span_set_dac.end()
        self.__update_status_return(str_status)
        self.save_values_to_file()

    def __update_status_return(self, str_status):
        list_pyboard_status = eval(str_status)
        assert len(list_pyboard_status) == 2
        self.b_pyboard_error = list_pyboard_status[0]
        self.i_pyboard_geophone_dac = list_pyboard_status[1]
        self.f_pyboard_geophone_read_s = time.perf_counter()

    def sync_status_get(self):
        """
        Poll for the pyboard_status
        """
        self.obj_time_span_get_status.start()
        str_status = self.fe.eval("micropython_logic.get_status()")
        self.obj_time_span_get_status.end()
        self.__update_status_return(str_status)

    def sync_set_user_led(self, on):
        assert isinstance(on, bool)
        self.fe.eval("micropython_logic.set_user_led({})".format(on))

    def sync_set_geophone_led_threshold_percent_FS(self, threshold_percent_FS):
        assert isinstance(threshold_percent_FS, float)
        assert 0.0 <= threshold_percent_FS <= 100.0
        threshold_dac = threshold_percent_FS * 4096.0 // 100.0
        assert 0.0 <= threshold_dac <= 4096
        self.fe.eval("micropython_logic.set_geophone_threshold_dac({})".format(threshold_dac))

    def debug_geophone_print(self):
        print(
            "geophone:                      dac={:016b}={:04d} [0..4095], voltage={:06f}mV, percent={:04.01f}".format(
                self.i_pyboard_geophone_dac,
                self.i_pyboard_geophone_dac,
                self.__read_geophone_voltage(),
                self.get_geophone_percent_FS(),
            )
        )

    def __sync_get_geophone(self):
        f_geophone_age_s = time.perf_counter() - self.f_pyboard_geophone_read_s
        if f_geophone_age_s > GEOPHONE_MAX_AGE_S:
            # This will read 'self.i_pyboard_geophone_dac'
            self.sync_status_get()

    def __read_geophone_voltage(self):
        self.__sync_get_geophone()
        return self.i_pyboard_geophone_dac * F_GEOPHONE_VOLTAGE_FACTOR

    def get_geophone_percent_FS(self):
        f_percent_FS = self.i_pyboard_geophone_dac / 4096.0 * 100.0
        return f_percent_FS

    def get_geophone_particle_velocity(self):
        return self.__read_geophone_voltage() / GEOPHONE_VOLTAGE_TO_PARTICLEVELOCITY_FACTOR

    #
    # Logic for 'calib_' only
    #
    def sync_calib_raw_init(self):
        """
        Initializes the AD20
        """
        self.fe.eval("micropython_logic.calib_raw_init()")

    def sync_calib_read_ADC24(self, iDac_index):
        strADC24 = self.fe.eval("micropython_logic.calib_read_ADC24({})".format(iDac_index))
        iADC24 = int(strADC24)

        fADC24 = convert_ADC24_signed_to_V(iADC24)
        return iADC24, fADC24

    def sync_calib_raw_measure(self, filename, iDac_index, iDacStart, iDacEnd):
        """
        Initializes the AD20
        """
        assert iDacStart >= 0
        assert iDacEnd < DAC20_MAX
        assert iDacStart < iDacEnd
        assert 0 <= iDac_index < DACS_COUNT
        self.fe.eval('micropython_logic.calib_raw_measure("{}", {}, {}, {})'.format(filename, iDac_index, iDacStart, iDacEnd))
        pass

    def calib_raw_readfile(self, filename):
        filenameFull = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        self.fe.get(filename, filenameFull)
