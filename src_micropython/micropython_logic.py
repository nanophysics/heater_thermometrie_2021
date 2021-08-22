import ubinascii
import ustruct
import time
from machine import Pin, I2C
from onewire import OneWire
from ds18x20 import DS18X20

import max7312
import sh1106
import max30205

VERSION = 'v0.91'
ZEILENHOEHE = 8+4


class OneWireID:
    def __init__(self):
        ow = OneWire(Pin('Y4'))
        self.temp = DS18X20(ow)


    def scan_ID(self):
        roms = self.temp.scan()
        assert len(roms) == 1, "Not (only) one sensor on the bus"
        # return ":".join(["{:02X}".format(x) for x in roms[0]])
        # return roms[0]
        return ubinascii.hexlify(roms[0]).decode("ascii")

    def read_temp(self, id):
        rom = ubinascii.unhexlify(id)
        self.temp.resolution(rom=rom, bits=12)
        self.temp.convert_temp()
        time.sleep(0.8) #conversion takes up to 750ms
        return self.temp.read_temp(rom)


class Display:
    def __init__(self, i2c):
        self._sh1106 = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3c)
        self._sh1106.sleep(False)
        self._sh1106.rotate(True, update=False)
        self._sh1106.contrast(255) # 0..255  brigtness
        self._sh1106.fill(0)

    def zeile(self, i, text):
        self._sh1106.text(text, 0, i * ZEILENHOEHE, 1)

    def clear(self):
        self._sh1106.fill(0)

    def show(self):
        self._sh1106.show()


class Proxy:
    def __init__(self):
        i2c_OLED = I2C(scl='Y9', sda='Y10', freq=40000)
        self.max30205 = max30205.MAX30205(i2c_OLED)
        self.display = Display(i2c_OLED)
        self.display_clear()
        self.onewireID = OneWireID()

    def display_clear(self):
        self.display.clear()
        self.display.zeile(0, '2020 %s' % VERSION)
        self.display.zeile(1, '%1.2fC' % 55.6)

    def get_defrost(self):
        return True
