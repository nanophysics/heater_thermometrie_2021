import ubinascii
import time
from machine import Pin, I2C
from onewire import OneWire
from ds18x20 import DS18X20
from micropython_ads1219 import ADS1219

import max7312
import sh1106
import max30205

from micropython_portable import Thermometrie

VERSION = "v0.1"

# Pins according to schematics
PIN_SDA_OLED = "Y10"
PIN_SCL_OLED = "Y9"
PIN_SDA_AD_DA = "X10"
PIN_SCL_AD_DA = "X9"
PIN_DEFROST = "X8"
PIN_SHORT_PT1000 = "X2"
PIN_SHORT_CARB = "X1"
PIN_DS18_SHORT = "X6"
PIN_DS18_PWD = "X5"
PIN_DS18_ID = "X4"
PIN_D18_TEMP = "Y4"
PIN_RESET = "X11"
PIN_DRDY = "X12"


class OnewireID:
    def __init__(self, pin=Pin(PIN_D18_TEMP)):
        assert isinstance(pin, Pin)
        ow = OneWire(pin)
        self.temp = DS18X20(ow)

    def scan(self):
        roms = self.temp.scan()
        if len(roms) == 0:
            return None
        assert len(roms) <= 1, "Maximum one sensor expected"
        return ubinascii.hexlify(roms[0]).decode("ascii")

    def read_temp(self, ident):
        rom = ubinascii.unhexlify(ident)
        self.temp.resolution(rom=rom, bits=12)
        self.temp.convert_temp()
        # conversion takes up to 750ms
        time.sleep(0.8)
        return self.temp.read_temp(rom)


class OnewireTail(OnewireID):
    def __init__(self):
        super().__init__(pin=Pin(PIN_DS18_ID))
        # DS18 in insert2019
        self.DS18_PWR = Pin(PIN_DS18_PWD, Pin.OUT_PP)
        self.DS18_SHORT = Pin(PIN_DS18_SHORT, Pin.OUT_PP)
        self.set_power(on=False)

    def set_power(self, on):
        # TODO(peter): Ist power on/off korrekt?
        isinstance(on, bool)
        self.DS18_PWR.value(on)
        self.DS18_SHORT.value(not on)
        # if on:
        #     # pin to power DA18 during conversion
        #     Pin('X3', Pin.IN)
        #     return
        # pin_power = Pin('X3', Pin.OUT_PP)
        # pin_power.value(True)


class TemperatureTail:
    def __init__(self):
        self.short_carb = Pin(PIN_SHORT_CARB, Pin.OUT_PP)
        self.short_pt1000 = Pin(PIN_SHORT_PT1000, Pin.OUT_PP)

        # ADC24
        # I2C(scl=Pin('X9'), sda=Pin('X10'), freq=400000)
        self.i2c_AD24 = I2C(1)
        self.reset = Pin(PIN_RESET, Pin.OUT_PP)
        # active low, deshalb auf 1
        self.reset.value(1)
        self.adc = ADS1219(self.i2c_AD24)
        # self.adc.set_channel(ADS1219.CHANNEL_AIN0_AIN1)
        self.adc.set_conversion_mode(ADS1219.CM_SINGLE)
        self.adc.set_vref(ADS1219.VREF_EXTERNAL)
        self.adc.set_gain(ADS1219.GAIN_1X)  # GAIN_1X, GAIN_4X
        self.adc.set_data_rate(ADS1219.DR_20_SPS)  # DR_20_SPS -> 50 ms

        self.set_thermometrie(on=False)

    def set_thermometrie(self, on):
        assert isinstance(on, bool)
        self.short_carb.value(not on)
        self.short_pt1000.value(not on)

    def get_voltage(self, carbon):
        assert isinstance(carbon, bool)
        channel = ADS1219.CHANNEL_AIN0_AIN1
        factor = Thermometrie.ADC24_FACTOR_PT1000
        if carbon:
            channel = ADS1219.CHANNEL_AIN2_AIN3
            factor = Thermometrie.ADC24_FACTOR_CARBON
        self.adc.set_channel(channel=channel)
        voltage = self.adc.read_data_signed() * Thermometrie.ADC24_FACTOR_PT1000
        return voltage

    # hw.adc.set_channel(ADS1219.CHANNEL_AIN2_AIN3) # carbon
    # voltage_carbon = hw.adc.read_data_signed() * electronics.ADC24_FACTOR_CARBON
    # hw.adc.set_channel(ADS1219.CHANNEL_AIN0_AIN1) # pt1000
    # voltage_pt1000 = hw.adc.read_data_signed() * electronics.ADC24_FACTOR_PT1000
    # print("voltage_carbon: %f V, voltage_pt1000: %f V" % (voltage_carbon, voltage_pt1000))
    # print("resistance_carbon: %f Ohm, resistance_pt1000: %f Ohm" % (voltage_carbon/electronics.CURRENT_A_CARBON, voltage_pt1000/electronics.CURRENT_A_PT1000))


class Display:
    ZEILENHOEHE = 8 + 4

    def __init__(self, i2c):
        self._sh1106 = sh1106.SH1106_I2C(128, 64, i2c, None, 0x3C)
        self._sh1106.sleep(False)
        self._sh1106.rotate(True, update=False)
        # 0..255  brigtness
        self._sh1106.contrast(255)
        self._sh1106.fill(0)

    def zeile(self, i, text):
        self._sh1106.text(text, 0, i * Display.ZEILENHOEHE, 1)

    def clear(self):
        self._sh1106.fill(0)

    def show(self):
        self._sh1106.show()


class Proxy:
    def __init__(self):
        self.defrost = Pin(PIN_DEFROST, Pin.IN)
        i2c_OLED = I2C(scl=PIN_SCL_OLED, sda=PIN_SDA_OLED, freq=40000)
        self.max30205 = max30205.MAX30205(i2c_OLED)
        self.display = Display(i2c_OLED)
        self.display_clear()
        self.onewire_id = OnewireID()
        self.onewire_tail = OnewireTail()
        self.temperature_tail = TemperatureTail()

    def display_clear(self):
        self.display.clear()
        self.display.zeile(0, "2020 %s" % VERSION)
        self.display.zeile(1, "%1.2fC" % 55.6)

    def get_defrost(self):
        return not self.defrost()
