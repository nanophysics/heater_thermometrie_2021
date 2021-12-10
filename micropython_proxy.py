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
    from mp.pyboard import PyboardError
except ModuleNotFoundError as ex:
    raise Exception('The module "mpfshell2" is missing. Did you call "pip -r requirements.txt"?') from ex

HWSERIAL_SIMULATE = "SIMULATE"

REQUIRED_MPFSHELL_VERSION = "100.9.17"
if mp.version.FULL < REQUIRED_MPFSHELL_VERSION:
    raise Exception(f'Your "mpfshell" has version "{mp.version.FULL}" but should be higher than "{REQUIRED_MPFSHELL_VERSION}". Call "pip install --upgrade mpfshell2"!')

HWTYPE_HEATER_THERMOMETRIE_2021 = "heater_thermometrie_2021"


class DisplayProxy:
    LINES = 5

    def __init__(self, proxy):
        self.proxy = proxy
        self.lines = [f"{'??':<16s}" for line in range(self.LINES)]

    def clear(self):
        self.lines = ["" for line in range(self.LINES)]

    def show_lines(self):
        self.proxy.eval_as_none(f"proxy.display.show_lines({self.lines})")

    def line(self, line: int, text: str):
        assert isinstance(line, int)
        assert 0 <= line < DisplayProxy.LINES
        assert isinstance(text, str)
        self.lines[line] = f"{text:<16s}"

    @property
    def sim_get(self):
        return self.lines


class OnewireBox:
    def __init__(self, proxy, name="proxy.onewire_box"):
        self._name = name
        self._proxy = proxy

    def scan(self) -> str:
        # '28E3212E0D00002E'
        rc = self._proxy.eval_as(str, f"{self._name}.scan()", accept_none=True)
        if rc is None:
            return ONEWIRE_ID_INSERT_NOT_CONNECTED
        return rc

    def read_temp_C(self, ident: str) -> float:
        assert isinstance(ident, str)
        assert len(ident) == 16
        return self._proxy.eval_as(float, f"{self._name}.read_temp_C('{ident}')", accept_none=True)


class OnewireInsert(OnewireBox):
    def __init__(self, proxy):
        super().__init__(proxy=proxy, name="proxy.onewire_insert")


class TemperatureInsert:
    def __init__(self, proxy):
        self.proxy = proxy

    def enable_thermometrie(self, enable: bool) -> None:
        assert isinstance(enable, bool)
        return self.proxy.eval_as_none(f"proxy.temperature_insert.enable_thermometrie(enable={enable})")

    def read_resistance_OHM(self, carbon=True) -> float:
        assert isinstance(carbon, bool)
        return self.proxy.eval_as(float, f"proxy.temperature_insert.read_resistance_OHM(carbon={carbon})")


class Heater:
    def __init__(self, proxy):
        self._proxy = proxy

    def set_power(self, power: int) -> None:
        assert not isinstance(power, bool)
        assert isinstance(power, int)
        assert 0 <= power < 2 ** 16
        return self._proxy.eval_as(str, f"proxy.heater.set_power(power={power})")


class DefrostSwitch:
    def __init__(self, proxy):
        self._proxy = proxy

    def is_on(self) -> bool:
        return self._proxy.eval_as(bool, "proxy.get_defrost()")


class MicropythonProxy:
    def __init__(self, fe):
        self.fe = fe

        # Start the program
        self._fe_exec("import main")
        self._fe_exec("main.enter_driver_mode()")
        self._fe_exec("proxy = main.proxy")

    def _fe_exec(self, cmd):
        try:
            self.fe.exec(cmd)
        except PyboardError as e:
            logger.error(f"ERROR on pyboard: '{cmd}' -> {e!r}")
            logger.exception(e)
            raise

    def _fe_eval(self, cmd):
        try:
            return self.fe.eval(cmd)
        except PyboardError as e:
            logger.error(f"ERROR on pyboard: '{cmd}' -> {e!r}")
            logger.exception(e)
            raise

    def eval_as(self, type_expected, cmd, accept_none=False):
        assert isinstance(cmd, str)
        result = self._fe_eval(cmd)
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
