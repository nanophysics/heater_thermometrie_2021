# -*- coding: utf-8 -*-

"""
    I2C-Interface to the MAX30205 "Human Body Temperature Sensor"
"""

import array
import pyb

# A2, A1, A0
I2C_ADDRESS_A = const(0x90)  # 0, 0, 0
I2C_ADDRESS_B = const(0x92)  # 0, 0, 1
I2C_ADDRESS_C = const(0x94)  # 0, 1, 0
I2C_ADDRESS_D = const(0x96)  # 0, 1, 1

REG_TEMP = const(0b00000000)
REG_CONFIG = const(0b00000001)
REG_T_HYST = const(0b00000010)
REG_T_OS = const(0b00000011)

REG_CONFIG_ONESHOT = const(0b10000000)
REG_CONFIG_TIMEOUT = const(0b01000000)
REG_CONFIG_DATAFORMAT = const(0b00100000)
REG_CONFIG_FAULTQUEUE = const(0b00011000)
REG_CONFIG_OSPOLARITY = const(0b00000100)
REG_CONFIG_COMPARATOR = const(0b00000010)
REG_CONFIG_SHUTDOWN = const(0b00000001)

TEMP_0C = const(0x0000)
TEMP_64C = const(0x4000)

CONVERSION_TIME_MS = 50


class MAX30205:
    def __init__(self, i2c):
        self.__i2c = i2c

    def __readTemp(self, i2cAddress, iRegister):
        """
        read temperature (2 bytes)
        """
        bTemp = self.__i2c.readfrom_mem(i2cAddress >> 1, iRegister, 2)
        iTemp = int((bTemp[0] << 8) | bTemp[1])
        fTemp = iTemp * 64.0 / TEMP_64C
        return fTemp

    def oneShotNormalA(self, i2cAddress):
        """
        Start Oneshot and Shutdown afterwards
        """
        self.__i2c.writeto_mem(i2cAddress >> 1, REG_CONFIG, array.array("b", (REG_CONFIG_ONESHOT | REG_CONFIG_SHUTDOWN,)))

    def oneShotNormalB(self, i2cAddress):
        fTemp = self.__readTemp(i2cAddress, REG_TEMP)
        return fTemp

    def oneShotNormal(self, i2cAddress):
        self.oneShotNormalA(i2cAddress)
        pyb.delay(CONVERSION_TIME_MS)
        return self.oneShotNormalB(i2cAddress)
