import time
import pathlib
import logging

import config_all
import calib_prepare_lib

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

HWSERIAL_SIMULATE = "SIMULATE"

REQUIRED_MPFSHELL_VERSION = "100.9.17"
if mp.version.FULL < REQUIRED_MPFSHELL_VERSION:
    raise Exception(f'Your "mpfshell" has version "{mp.version.FULL}" but should be higher than "{REQUIRED_MPFSHELL_VERSION}". Call "pip install --upgrade mpfshell2"!')

HWTYPE_HEATER_THERMOMETRIE_2021 = "heater_thermometrie_2021"


class FeSimulator:
    def exec(self, cmd: str) -> None:
        pass

    def eval(self, cmd: str):
        if cmd.startswith("proxy.display."):
            return b"None"
        if cmd == "proxy.onewire_id.scan()":
            return b"28E3212E0D00002E"
        if cmd == "proxy.onewire_id.read_temp('28E3212E0D00002E')":
            return b"42.42"
        if cmd.startswith("proxy.onewire_tail.set_power("):
            return b"None"
        if cmd == "proxy.onewire_tail.scan()":
            return b"28E3212E0D00002F"
        if cmd == "proxy.onewire_tail.read_temp('28E3212E0D00002F')":
            return b"43.43"
        if cmd == "proxy.get_defrost()":
            return b"True"
        if cmd.startswith("proxy.temperature_tail.set_thermometrie(on="):
            return b"None"
        if cmd.startswith("proxy.temperature_tail.get_voltage(carbon="):
            return b"4.711"
        if cmd.startswith("proxy.heater.set_power(power="):
            return b"None"
        assert NotImplementedError()

    def close(self):
        pass


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


class Heater:
    def __init__(self, proxy):
        self.proxy = proxy

    def set_power(self, power: int) -> None:
        assert isinstance(power, int)
        assert 0 <= power < 2 ** 16
        return self.proxy.eval_as(str, f"proxy.heater.set_power(power={power})")


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

    def get_defrost(self) -> bool:
        return self.eval_as(bool, "proxy.get_defrost()")


class MicropythonInterface:
    def __init__(self, hwserial):
        if hwserial == HWSERIAL_SIMULATE:
            self.heater_thermometrie_2021_serial = "v42"
            self.fe = FeSimulator()
        else:
            logger.warn(f"******************* {hwserial}")
            self._init_pyboard(hwserial=hwserial)

    def close(self):
        self.fe.close()

    def _init_pyboard(self, hwserial=""):
        hwserial = hwserial.strip()
        if hwserial == "":
            hwserial = None
        self.board = mp.pyboard_query.ConnectHwtypeSerial(
            product=mp.pyboard_query.Product.Pyboard,
            hwtype=HWTYPE_HEATER_THERMOMETRIE_2021,
            hwserial=hwserial,
        )
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

        self.shell = self.board.mpfshell
        self.fe = self.shell.MpFileExplorer
        # Download the source code
        self.shell.sync_folder(
            DIRECTORY_OF_THIS_FILE / "src_micropython",
            FILES_TO_SKIP=["config_identification.py"],
        )

    def init(self):
        self.proxy = MicropythonProxy(self.fe)
        self.display = DisplayProxy(self.proxy)
        self.onewire_id = OnewireID(self.proxy)
        self.onewire_tail = OnewireTail(self.proxy)
        self.temperature_tail = TemperatureTail(self.proxy)
        self.heater = Heater(self.proxy)

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

        self.temperature_tail.set_thermometrie(on=True)
        for carbon, label, current_factor in (
            (True, "carbon", Thermometrie.CURRENT_A_CARBON),
            (False, "PT1000", Thermometrie.CURRENT_A_PT1000),
        ):
            temperature_V = self.temperature_tail.get_voltage(carbon=carbon)
            print("%s: %f V, %f Ohm" % (label, temperature_V, temperature_V / current_factor))

        self.temperature_tail.set_thermometrie(on=False)

        self.heater.set_power(power=2 ** 15 - 1)
        time.sleep(1.5)
        self.heater.set_power(power=2 ** 16 - 1)
        time.sleep(0.5)
        self.heater.set_power(power=0)

        # temperature_V = self.temperature_tail.get_voltage(carbon=True)
        # print("voltage_carbon: %f V," % temperature_V)
        # temperature_V = self.temperature_tail.get_voltage(carbon=False)
        # print("voltage_ptc1000: %f V," % temperature_V)

        # print("voltage_carbon: %f V, voltage_pt1000: %f V" % (voltage_carbon, voltage_pt1000))
        # print("resistance_carbon: %f Ohm, resistance_pt1000: %f Ohm" % (voltage_carbon/electronics.CURRENT_A_CARBON, voltage_pt1000/electronics.CURRENT_A_PT1000))

    def get_defrost(self) -> bool:
        return self.proxy.get_defrost()
