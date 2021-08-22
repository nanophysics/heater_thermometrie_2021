import config_all
import calib_prepare_lib
import os
import sys
import re
import math
import time
import pathlib
import logging

from mp.micropythonshell import FILENAME_IDENTIFICATION

from src_micropython import micropython_portable
from src_micropython.micropython_portable import Thermometrie

"""
    Separation of logic
        pyboard
            every x ms: polls for the geophone
            every x ms: initializes DAC20. But only if no traffic detected
            flashes the red geophone led if movement detected
            flashed the blue communication led if traffic detected
            keeps track of status:
                pyboard_status
                    b_error: if the driver is not working anymore
                    i_geophone_dac
                    i_geophone_age_ms
                This status may be retreived from the pyboard using get_status()
            update of DAC20/DAC12:
                set_dac(str_dac20, str_dac12):
                    sets both DAC20 and DAC12
                    pyboard_status
        pc-driver
            cache all 10 f_dac_v
            cache f_last_dac_set_s (the time the DACs where set the last time)
            cache pyboard_status

"""

logger = logging.getLogger("heater_thermometrie_2012")

logger.setLevel(logging.DEBUG)

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent
try:
    import mp
    import mp.version
    import mp.micropythonshell
    import mp.pyboard_query
except ModuleNotFoundError as ex:
    raise Exception('The module "mpfshell2" is missing. Did you call "pip -r requirements.txt"?')

REQUIRED_MPFSHELL_VERSION = "100.9.13"
if mp.version.FULL < REQUIRED_MPFSHELL_VERSION:
    raise Exception(f'Your "mpfshell" has version "{mp.version.FULL}" but should be higher than "{REQUIRED_MPFSHELL_VERSION}". Call "pip install --upgrade mpfshell2"!')


HWTYPE_HEATER_THERMOMETRIE_2021 = "heater_thermometrie_2021"

# ranges and scaling
DICT_GAIN_2_VALUE = {
    "+/- 10 V, change by hand": 1.0,
    "+/- 5 V, change by hand": 0.5,
    "+/- 2 V, change by hand": 0.2,
    "+/- 1 V, change by hand": 0.1,
    "+/- 0.5 V, change by hand": 0.05,
    "+/- 0.2 V, change by hand": 0.02,
    "+/- 0.1 V, change by hand": 0.01,
}
CHANGE_BY_HAND = ", change by hand"

# datasheet RTC-10hz, 395ohm, at 1000 Ohm RL 19.7 V/(m/s)
GEOPHONE_VOLTAGE_TO_PARTICLEVELOCITY_FACTOR = 19.7
# gainINA103 = 1000, dividerR49R51 = 0.33,  VrefMCP3201 = 3.3 therefore VrefMCP3201/gainINA103/dividerR49R51 = 0.01
F_GEOPHONE_VOLTAGE_FACTOR = 0.01 / 4096.0
GEOPHONE_MAX_AGE_S = 1.0

# sweep set interval, in seconds
F_SWEEPINTERVAL_S = 0.03


class DisplayProxy:
    def __init__(self, proxy):
        self.proxy = proxy

    def clear(self):
        self.proxy.eval_as_none("proxy.display.clear()")

    def show(self):
        self.proxy.eval_as_none("proxy.display.show()")

    def zeile(self, line: int, text: str):
        assert isinstance(line, int)
        assert 0 <= line <= 4
        assert isinstance(text, str)
        cmd = f'proxy.display.zeile({line}, "{text}")'
        self.proxy.eval_as_none(f"proxy.display.zeile({line}, '{text}')")


class OnewireID:
    def __init__(self, proxy):
        self.proxy = proxy

    def scan(self) -> str:
        # '28E3212E0D00002E'
        return self.proxy.eval_as(str, "proxy.onewire_id.scan()")

    def read_temp(self, ident: str) -> float:
        assert isinstance(ident, str)
        assert len(ident) == 16
        return self.proxy.eval_as(float, f"proxy.onewire_id.read_temp('{ident}')")


class OnewireTail:
    def __init__(self, proxy):
        self.proxy = proxy

    def set_power(self, on: bool) -> None:
        isinstance(on, bool)
        return self.proxy.eval_as_none(f"proxy.onewire_tail.set_power(on={on})")

    def scan(self) -> str:
        # '28E3212E0D00002E'
        return self.proxy.eval_as(str, "proxy.onewire_tail.scan()", accept_none=True)

    def read_temp(self, ident: str) -> float:
        assert isinstance(ident, str)
        assert len(ident) == 16
        return self.proxy.eval_as(float, f"proxy.onewire_tail.read_temp('{ident}')")


class TemperatureTail:
    def __init__(self, proxy):
        self.proxy = proxy

    def set_thermometrie(self, on: bool) -> None:
        assert isinstance(on, bool)
        return self.proxy.eval_as_none(f"proxy.temperature_tail.set_thermometrie(on={on})")

    def get_voltage(self, carbon=True) -> float:
        assert isinstance(carbon, bool)
        return self.proxy.eval_as(float, f"proxy.temperature_tail.get_voltage(carbon={carbon})")

    # hw.adc.set_channel(ADS1219.CHANNEL_AIN2_AIN3) # carbon
    # voltage_carbon = hw.adc.read_data_signed() * electronics.ADC24_FACTOR_CARBON
    # hw.adc.set_channel(ADS1219.CHANNEL_AIN0_AIN1) # pt1000
    # voltage_pt1000 = hw.adc.read_data_signed() * electronics.ADC24_FACTOR_PT1000
    # print("voltage_carbon: %f V, voltage_pt1000: %f V" % (voltage_carbon, voltage_pt1000))
    # print("resistance_carbon: %f Ohm, resistance_pt1000: %f Ohm" % (voltage_carbon/electronics.CURRENT_A_CARBON, voltage_pt1000/electronics.CURRENT_A_PT1000))

    # SHORT_CARB = Pin('X1', Pin.OUT_PP)
    # SHORT_PT1000 = Pin('X2', Pin.OUT_PP)

    # thermometrie_running = True
    # if thermometrie_running:
    #     SHORT_CARB.value(0)
    #     SHORT_PT1000.value(0)
    # else:
    #     SHORT_CARB.value(1)
    #     SHORT_PT1000.value(1)


class MicropythonProxy:
    def __init__(self, fe):
        self.fe = fe

        # Start the program
        self.fe.exec("import micropython_logic")
        self.fe.exec("proxy = micropython_logic.Proxy()")

        # hw.DS18_PWR
        # One wire in heater

        # One wire on insert
        # ow = OneWire(Pin('X4'))
        # temp_insert = DS18X20(ow)

    def eval_as(self, type_expected, cmd, accept_none=False):
        assert isinstance(cmd, str)
        result = self.fe.eval(cmd)
        assert isinstance(result, bytes)
        if accept_none:
            if result == b"None":
                return None
        if type_expected == str:
            return result.decode("ascii")
        value = eval(result)
        assert isinstance(value, type_expected)
        return value

    def eval_as_none(self, cmd):
        self.eval_as(type_expected=type(None), cmd=cmd)

    def get_defrost(self):
        return self.eval_as(bool, "proxy.get_defrost()")


class HeaterThermometrie2021:
    def __init__(self, board=None, hwserial=""):
        if board is not None:
            assert hwserial == ""
            self.board = board
        else:
            assert board is None
            hwserial = hwserial.strip()
            if hwserial == "":
                hwserial = None
            self.board = mp.pyboard_query.ConnectHwtypeSerial(product=mp.pyboard_query.Product.Pyboard, hwtype=HWTYPE_HEATER_THERMOMETRIE_2021, hwserial=hwserial)
        assert isinstance(self.board, mp.pyboard_query.Board)
        self.board.systemexit_hwtype_required(hwtype=HWTYPE_HEATER_THERMOMETRIE_2021)
        self.board.systemexit_firmware_required(min="1.14.0", max="1.14.0")
        self.heater_thermometrie_2021_serial = self.board.identification.HWSERIAL
        try:
            self.compact_2012_config = config_all.dict_compact2012[self.heater_thermometrie_2021_serial]
        except KeyError:
            self.compact_2012_config = config_all.dict_compact2012[config_all.SERIAL_UNDEFINED]
            print()
            print(f'WARNING: The connected "compact_2012" has serial "{self.heater_thermometrie_2021_serial}". However, this serial in unknown!')
            serials_defined = sorted(config_all.dict_compact2012.keys())
            serials_defined.remove(config_all.SERIAL_UNDEFINED)
            print(f'INFO: "config_all.py" lists these serials: {",".join(serials_defined)}')

        print(f"INFO: {HWTYPE_HEATER_THERMOMETRIE_2021} connected: {self.compact_2012_config}")

        self.__calibrationLookup = None
        self.ignore_str_dac12 = False
        self.f_write_file_time_s = 0.0
        self.filename_values = DIRECTORY_OF_THIS_FILE / f"Values-{self.heater_thermometrie_2021_serial}.txt"

        # The time when the dac was set last.
        self.f_last_dac_set_s = 0.0

        # if the driver is not working anymore
        self.b_pyboard_error = False
        self.i_pyboard_geophone_dac = 0
        self.f_pyboard_geophone_read_s = 0

        self.shell = self.board.mpfshell
        self.fe = self.shell.MpFileExplorer
        # Download the source code
        self.shell.sync_folder(DIRECTORY_OF_THIS_FILE / "src_micropython", FILES_TO_SKIP=["config_identification.py"])

        self.proxy = MicropythonProxy(self.fe)
        self.display = DisplayProxy(self.proxy)
        self.onewire_id = OnewireID(self.proxy)
        self.onewire_tail = OnewireTail(self.proxy)
        self.temperature_tail = TemperatureTail(self.proxy)

        self.display.clear()
        self.display.zeile(0, "heater")
        self.display.zeile(1, " _thermometrie")
        self.display.zeile(2, " _2021")
        self.display.zeile(3, "ETH Zuerich")
        self.display.zeile(4, "Peter Maerki")

        self.display.show()

        ident = self.onewire_id.scan()
        if ident is not None:
            temp = self.onewire_id.read_temp(ident=ident)
            print(f"ID vom heater_thermometrie_2021={ident} temp={temp}")

        self.onewire_tail.set_power(on=True)
        ident = self.onewire_tail.scan()
        if ident is not None:
            temp = self.onewire_tail.read_temp(ident=ident)
            print(f"ID vom tail={ident} temp={temp}")
        else:
            print(f"Onewire of tail did not respond")
        self.onewire_tail.set_power(on=False)

        defrost = self.proxy.get_defrost()

        self.temperature_tail.set_thermometrie(on=True)
        for carbon, label, current_factor in (
            (True, "carbon", Thermometrie.CURRENT_A_CARBON),
            (False, "PT1000", Thermometrie.CURRENT_A_PT1000),
        ):
            temperature_V = self.temperature_tail.get_voltage(carbon=carbon)
            print("%s: %f V, %f Ohm" % (label, temperature_V, temperature_V / current_factor))

        self.temperature_tail.set_thermometrie(on=False)

        # temperature_V = self.temperature_tail.get_voltage(carbon=True)
        # print("voltage_carbon: %f V," % temperature_V)
        # temperature_V = self.temperature_tail.get_voltage(carbon=False)
        # print("voltage_ptc1000: %f V," % temperature_V)

        # print("voltage_carbon: %f V, voltage_pt1000: %f V" % (voltage_carbon, voltage_pt1000))
        # print("resistance_carbon: %f Ohm, resistance_pt1000: %f Ohm" % (voltage_carbon/electronics.CURRENT_A_CARBON, voltage_pt1000/electronics.CURRENT_A_PT1000))

        return
        self.sync_status_get()

        self.load_calibration_lookup()

    def close(self):
        self.fe.close()

    def load_calibration_lookup(self):
        if self.heater_thermometrie_2021_serial is None:
            return
        calib_correction_data = calib_prepare_lib.CalibCorrectionData(self.heater_thermometrie_2021_serial)
        self.__calibrationLookup = calib_correction_data.load()

    def reset_calibration_lookup(self):
        self.__calibrationLookup = None

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
        b_done, b_need_wait_before_DAC_set, dict_changed_values = self.__calculate_and_set_new_dac(dict_requested_values)

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
        print("geophone:                      dac={:016b}={:04d} [0..4095], voltage={:06f}mV, percent={:04.01f}".format(self.i_pyboard_geophone_dac, self.i_pyboard_geophone_dac, self.__read_geophone_voltage(), self.get_geophone_percent_FS()))

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
