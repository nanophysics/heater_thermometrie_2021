#
# heater_thermometrie_2021
#
# This file contains production-data of all heater_thermometrie_2021 which where produced.
#
import logging

logger = logging.getLogger("LabberDriver")

SERIAL_UNDEFINED = "UNDEFINED"
ONEWIRE_ID_HEATER_UNDEFINED = "UNDEFINED"
ONEWIRE_ID_INSERT_UNDEFINED = "UNDEFINED"
ONEWIRE_ID_INSERT_NOT_CONNECTED = "NOT_CONNECTED"
dict_heater2021 = {}
dict_insert = {}


class ConfigHeater2021:
    def __init__(self, HWSERIAL, HARDWARE_VERSION, COMMENT, ONEWIRE_ID_HEATER):
        dict_heater2021[HWSERIAL] = self
        self.HWSERIAL = HWSERIAL
        self.HARDWARE_VERSION = HARDWARE_VERSION
        self.COMMENT = COMMENT
        self.ONEWIRE_ID_HEATER = ONEWIRE_ID_HEATER

    def __repr__(self):
        return f"{self.HWSERIAL}, hardware version {self.HARDWARE_VERSION}, {self.COMMENT}"

    @staticmethod
    def load_config(serial: str) -> dict:
        try:
            return dict_heater2021[serial]
        except KeyError:
            logger.warning(f'The connected "heater_thermometrie_2021" has serial "{serial}". However, this serial in unknown!')
            serials_defined = sorted(dict_heater2021.keys())
            serials_defined.remove(SERIAL_UNDEFINED)
            logger.warning(f'"config_all.py" lists these serials: {",".join(serials_defined)}')
            return dict_heater2021[SERIAL_UNDEFINED]


class ConfigInsert:
    def __init__(self, ONEWIRE_ID, HWSERIAL, COMMENT):
        dict_insert[ONEWIRE_ID] = self
        self.ONEWIRE_ID = ONEWIRE_ID
        self.HWSERIAL = HWSERIAL
        self.COMMENT = COMMENT

    def __repr__(self):
        return f"{self.HWSERIAL}, onewireid {self.ONEWIRE_ID}, {self.COMMENT}"

    @property
    def __name__(self):
        "pytest test name"
        return self.HWSERIAL

    @staticmethod
    def load_config(onewire_id: str) -> dict:
        try:
            return dict_insert[onewire_id]
        except KeyError:
            logger.warning(f'The connected "insert" has a onewire serial "{onewire_id}". However, this serial in unknown!')
            ids_defined = sorted(dict_insert.keys())
            ids_defined.remove(ONEWIRE_ID_INSERT_UNDEFINED)
            logger.warning(f'"config_all.py" lists these ids for inserts: {",".join(ids_defined)}')
            return dict_insert[ONEWIRE_ID_INSERT_UNDEFINED]


ConfigHeater2021(
    SERIAL_UNDEFINED,
    HARDWARE_VERSION="2021",
    COMMENT="Serial not defined, hardware unknown! Assuming a bare micropython board.",
    ONEWIRE_ID_HEATER=ONEWIRE_ID_HEATER_UNDEFINED,
)

ConfigHeater2021(
    "20210601_01",
    HARDWARE_VERSION="2021",
    COMMENT="Prototype 2021",
    ONEWIRE_ID_HEATER="28e3212e0d00002e",
)

ConfigInsert(
    ONEWIRE_ID=ONEWIRE_ID_INSERT_NOT_CONNECTED,
    HWSERIAL="unknown",
    COMMENT="Onewire ID could not be read: Insert not connected!",
)

ConfigInsert(
    ONEWIRE_ID=ONEWIRE_ID_INSERT_UNDEFINED,
    HWSERIAL="unknown",
    COMMENT="Onewire ID not defined, insert unknown!",
)

ConfigInsert(
    ONEWIRE_ID="28d821950d00003e",
    HWSERIAL="20171228_03",
    COMMENT="Blue Testbox Fischer 104",
)

ConfigInsert(
    ONEWIRE_ID="289986980d000083",
    HWSERIAL="20210916_proto",
    COMMENT="First proto insert_2019",
)

