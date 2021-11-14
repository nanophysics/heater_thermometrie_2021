import time
import pathlib
import logging

from micropython_proxy import (
    MicropythonProxy,
    DisplayProxy,
    OnewireBox,
    OnewireInsert,
    TemperatureInsert,
    Heater,
    DefrostSwitch,
    mp,
    HWSERIAL_SIMULATE,
    HWTYPE_HEATER_THERMOMETRIE_2021,
)
from micropython_proxy_simulator import FeSimulator

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent

logger = logging.getLogger("LabberDriver")

TICK_INTERVAL_S = 1.0


class Timebase:
    def __init__(self, realtime_factor: float = None):
        if realtime_factor is None:
            realtime_factor = 1.0
        assert isinstance(realtime_factor, float)
        self._realtime_factor = realtime_factor

    @property
    def now_s(self) -> float:
        return time.time() * self._realtime_factor

    def sleep(self, duration_s: float):
        assert isinstance(duration_s, float)

        duration_s = max(TICK_INTERVAL_S / 10.0, duration_s)
        time.sleep(duration_s / self._realtime_factor)


class TimebaseSimulation:
    def __init__(self):
        self.now_s = 0.0

    def sleep(self, duration_s: float):
        assert isinstance(duration_s, float)
        self.now_s += duration_s


class MicropythonInterface:
    def __init__(self, hwserial, force_use_realtime_factor=1.0):
        self.proxy = None
        self.display = None
        self.onewire_box = None
        self.onewire_insert = None
        self.temperature_insert = None
        self.heater = None
        self.defrost_switch = None

        if (force_use_realtime_factor is not None) or (hwserial != HWSERIAL_SIMULATE):
            self.timebase = Timebase(realtime_factor=force_use_realtime_factor)
        else:
            self.timebase = TimebaseSimulation()
        if hwserial == HWSERIAL_SIMULATE:
            self.heater_thermometrie_2021_serial = "v42"
            self.fe = FeSimulator()
            self.sim_update_time = self.fe.sim_update_time
            self.sim_set_resistance_OHM = self.fe.sim_set_resistance_OHM
            self.sim_set_resistance_OHM = self.fe.sim_set_resistance_OHM
            self.sim_set_insert_onewire_id = self.fe.proxy.onewire_insert.sim_set_onewire_id
        else:
            logger.warning(f"******************* {hwserial}")
            self._init_pyboard(hwserial=hwserial)
            self.sim_update_time = lambda time_now_s: None
            self.sim_set_resistance_OHM = lambda carbon, temperature_K: None
            self.sim_set_insert_onewire_id = lambda onewire_id: None

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
        self.onewire_box = OnewireBox(self.proxy)
        self.onewire_insert = OnewireInsert(self.proxy)
        self.temperature_insert = TemperatureInsert(self.proxy)
        self.heater = Heater(self.proxy)
        self.defrost_switch = DefrostSwitch(self.proxy)

        self.display.clear()
        self.display.line(2, "      ...")
        self.display.show_lines()

        # self.temperature_insert.enable_thermometrie(enable=False)
        # self.heater.set_power(power=2 ** 15 - 1)
        # self.timebase.sleep(1.5)
        # self.heater.set_power(power=2 ** 16 - 1)
        # self.timebase.sleep(0.5)
        # self.heater.set_power(power=0)
