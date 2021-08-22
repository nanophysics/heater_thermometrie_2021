# pylint: disable=import-error
from micropython import const

CTRL_WRITE_DAC = const(0b00010000)


class DAC8571:
    def __init__(self, i2c, address=0x4C):
        self._i2c = i2c
        self._address = address

    def write_dac(self, dac):
        assert 0 <= dac < 2 ** 16
        self._i2c.writeto(self._address, bytearray((CTRL_WRITE_DAC, 0xFF & (dac >> 8), 0xFF & dac)))
