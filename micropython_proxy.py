import pathlib
import logging

from config_all import ONEWIRE_ID_INSERT_NOT_CONNECTED

logger = logging.getLogger("LabberDriver")

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent
try:
    import mp
    import mp.version
    import mp.micropythonshell
    import mp.pyboard_query
except ModuleNotFoundError as ex:
    raise Exception('The module "mpfshell2" is missing. Did you call "pip -r requirements.txt"?') from ex

HWSERIAL_SIMULATE = "SIMULATE"

REQUIRED_MPFSHELL_VERSION = "100.9.17"
if mp.version.FULL < REQUIRED_MPFSHELL_VERSION:
    raise Exception(f'Your "mpfshell" has version "{mp.version.FULL}" but should be higher than "{REQUIRED_MPFSHELL_VERSION}". Call "pip install --upgrade mpfshell2"!')

HWTYPE_HEATER_THERMOMETRIE_2021 = "heater_thermometrie_2021"


class DisplayProxy:
    def __init__(self, proxy):
        self.proxy = proxy

    def clear(self):
        self.proxy.eval_as_none("proxy().display.clear()")

    def show(self):
        self.proxy.eval_as_none("proxy().display.show()")

    def zeile(self, line: int, text: str):
        assert isinstance(line, int)
        assert 0 <= line <= 4
        assert isinstance(text, str)
        cmd = f'proxy.display.zeile({line}, "{text}")'
        self.proxy.eval_as_none(f"proxy().display.zeile({line}, '{text}')")


class OnewireBox:
    def __init__(self, proxy, name="proxy().onewire_box"):
        self._name = name
        self._proxy = proxy

    def scan(self) -> str:
        # '28E3212E0D00002E'
        rc = self._proxy.eval_as(str, f"{self._name}.scan()", accept_none=True)
        if rc is None:
            return ONEWIRE_ID_INSERT_NOT_CONNECTED
        return rc

    def read_temp(self, ident: str) -> float:
        assert isinstance(ident, str)
        assert len(ident) == 16
        return self._proxy.eval_as(float, f"{self._name}.read_temp('{ident}')", accept_none=True)


class OnewireInsert(OnewireBox):
    def __init__(self, proxy):
        super().__init__(proxy=proxy, name="proxy().onewire_insert")


class TemperatureInsert:
    def __init__(self, proxy):
        self.proxy = proxy

    def enable_thermometrie(self, enable: bool) -> None:
        assert isinstance(enable, bool)
        return self.proxy.eval_as_none(f"proxy().temperature_insert.enable_thermometrie(enable={enable})")

    def read_resistance_OHM(self, carbon=True) -> float:
        assert isinstance(carbon, bool)
        return self.proxy.eval_as(float, f"proxy().temperature_insert.read_resistance_OHM(carbon={carbon})")

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
        self._proxy = proxy

    def set_power(self, power: int) -> None:
        assert isinstance(power, int)
        assert 0 <= power < 2 ** 16
        return self._proxy.eval_as(str, f"proxy().heater.set_power(power={power})")


class DefrostSwitch:
    def __init__(self, proxy):
        self._proxy = proxy

    def is_on(self) -> bool:
        return self._proxy.eval_as(bool, "proxy().get_defrost()")


class MicropythonProxy:
    def __init__(self, fe):
        self.fe = fe

        # Start the program
        self.fe.exec("import main")
        self.fe.exec("proxy = main.proxy")
        # self.fe.exec("import micropython_logic")
        # self.fe.exec("proxy = micropython_logic.Proxy()")

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
        value = eval(result)  # pylint: disable=eval-used
        assert isinstance(value, type_expected)
        return value

    def eval_as_none(self, cmd):
        self.eval_as(type_expected=type(None), cmd=cmd)
