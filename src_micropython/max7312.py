# pylint: disable=undefined-variable
# pylint: disable=import-error

import pyb

REG_OUTPUT = const(0x02)
REG_POLARITY_INVERSION = const(0x04)  # (1=data inverted)
REG_DIRECTION = const(0x06)  # (0=output, 1=input)

RELAIS_PULSE_MS = 20


class MAX7312_port:
    def __init__(self, i2c, addr, register):
        self.__i2c = i2c
        self.__addr = addr
        self.__register = register

    def set(self, relais, on):
        value = 0x01 << (relais - 1)
        if not on:
            value = 0x9F ^ value
        self.__i2c.writeto_mem(self.__addr, self.__register, bytearray([value]))
        pyb.delay(RELAIS_PULSE_MS)
        self.__i2c.writeto_mem(self.__addr, self.__register, b"\x00")


class MAX7312:
    def __init__(self, i2c, addr):
        self.__addr = addr
        self.port1 = MAX7312_port(i2c, addr, REG_OUTPUT)
        self.port2 = MAX7312_port(i2c, addr, REG_OUTPUT + 1)

        i2c.writeto_mem(self.__addr, REG_OUTPUT, b"\x00\x00")
        i2c.writeto_mem(self.__addr, REG_POLARITY_INVERSION, b"\x00\x00")
        i2c.writeto_mem(self.__addr, REG_DIRECTION, b"\x00\x00")

    def set(self, relais, on):
        if relais > 5:
            self.port2.set(relais - 5, on)
            return
        self.port1.set(relais, on)


class Board:
    def __init__(self, i2c, addr):
        self.max7312_01_10 = MAX7312(i2c, addr)
        self.max7312_11_20 = MAX7312(i2c, addr + 1)

    def set(self, relais, on):
        if relais > 10:
            self.max7312_11_20.set(relais - 10, on)
            return
        self.max7312_01_10.set(relais, on)
