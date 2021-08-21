from machine import I2C

import max7312
import sh1106
import max30205

VERSION = 'v0.91'
ZEILENHOEHE = 8+4


class Display:
    def __init__(self, i2c):
        self.__sh1106 = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3c)
        self.__sh1106.sleep(False)
        self.__sh1106.contrast(255) # 0..255  brigtness
        self.__sh1106.fill(0)

    def zeile(self, i, text):
        self.__sh1106.text(text, 0, i * ZEILENHOEHE, 1)

    def clear(self):
        self.__sh1106.fill(0)

    def show(self):
        self.__sh1106.show()


class ScannerPyb2020:
    def __init__(self):
        i2c_OLED = I2C(scl='Y9', sda='Y10', freq=40000)
        self.max30205 = max30205.MAX30205(i2c_OLED)
        self.display = Display(i2c_OLED)
        self.display_clear()

    def display_clear(self):
        self.display.clear()
        self.display.zeile(0, '2020 %s' % VERSION)
        self.display.zeile(1, '%1.2fC' % 55.6)

    def get_defrost(self):
        return True
