#
# heater_thermometrie_2021
#
# This file contains production-data of all heater_thermometrie_2021 which where produced.
#
SERIAL_UNDEFINED = "SERIAL_UNDEFINED"
dict_heater2021 = {}


class ConfigHeater2021:
    def __init__(self, HWSERIAL, HARDWARE_VERSION, COMMENT):
        dict_heater2021[HWSERIAL] = self
        self.HWSERIAL = HWSERIAL
        self.HARDWARE_VERSION = HARDWARE_VERSION
        self.COMMENT = COMMENT

    def __repr__(self):
        return f"serial '{self.HWSERIAL}' with Hardware '{self.HARDWARE_VERSION}' ({self.COMMENT})"


ConfigHeater2021(SERIAL_UNDEFINED, HARDWARE_VERSION="2021", COMMENT="Serial not defined, hardware unknown! Assuming a bare micropython board.")

ConfigHeater2021("20210601_01", HARDWARE_VERSION="2021", COMMENT="Prototype 2021")
