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
    mp,
    FeSimulator,
    HWSERIAL_SIMULATE,
    HWTYPE_HEATER_THERMOMETRIE_2021,
)
from src_micropython.micropython_portable import Thermometrie

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent

logger = logging.getLogger("LabberDriver")


class MicropythonInterface:
    def __init__(self, hwserial):
        self.proxy = None
        self.display = None
        self.onewire_box = None
        self.onewire_insert = None
        self.temperature_insert = None
        self.heater = None

        if hwserial == HWSERIAL_SIMULATE:
            self.heater_thermometrie_2021_serial = "v42"
            self.fe = FeSimulator()
        else:
            logger.warning(f"******************* {hwserial}")
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

        self.display.clear()
        self.display.zeile(0, "heater")
        self.display.zeile(1, " _thermometrie")
        self.display.zeile(2, " _2021")
        self.display.zeile(3, "ETH Zuerich")
        self.display.zeile(4, "Peter Maerki")

        self.display.show()

        if False:
            self.onewire_insert.set_power(on=True)
            ident = self.onewire_insert.scan()
            if ident is not None:
                temp = self.onewire_insert.read_temp(ident=ident)
                print(f"ID vom insert={ident} temp={temp}")
            else:
                print("Onewire of insert did not respond")
            self.onewire_insert.set_power(on=False)

        self.temperature_insert.set_thermometrie(on=True)
        for carbon, label, current_factor in (
            (True, "carbon", Thermometrie.CURRENT_A_CARBON),
            (False, "PT1000", Thermometrie.CURRENT_A_PT1000),
        ):
            temperature_V = self.temperature_insert.get_voltage(carbon=carbon)
            print(f"{label}: {temperature_V:f} V, {temperature_V / current_factor:f} Ohm")

        self.temperature_insert.set_thermometrie(on=False)

        self.heater.set_power(power=2 ** 15 - 1)
        time.sleep(1.5)
        self.heater.set_power(power=2 ** 16 - 1)
        time.sleep(0.5)
        self.heater.set_power(power=0)

        # temperature_V = self.temperature_insert.get_voltage(carbon=True)
        # print("voltage_carbon: %f V," % temperature_V)
        # temperature_V = self.temperature_insert.get_voltage(carbon=False)
        # print("voltage_ptc1000: %f V," % temperature_V)

        # print("voltage_carbon: %f V, voltage_pt1000: %f V" % (voltage_carbon, voltage_pt1000))
        # print("resistance_carbon: %f Ohm, resistance_pt1000: %f Ohm" % (voltage_carbon/electronics.CURRENT_A_CARBON, voltage_pt1000/electronics.CURRENT_A_PT1000))

    def get_defrost(self) -> bool:
        return self.proxy.get_defrost()
