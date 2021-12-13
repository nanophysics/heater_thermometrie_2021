# pylint: disable=import-error
# pylint: disable=consider-using-f-string

import time

# import errno
import ubinascii
from machine import Pin, I2C, WDT

from onewire import OneWire
from ds18x20 import DS18X20
from ads1219 import ADS1219
from sh1106 import SH1106_I2C
from dac8571 import DAC8571

from micropython_defrost import DefrostProcess
from micropython_portable import ThermometrieCarbon, ThermometriePT1000

VERSION = "v0.9"

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
PIN_DS18_TEMP = "Y4"
PIN_ADS1219_RESET = "X11"
PIN_ADS1219_DRDY = "X12"


class AttrsCarbon(ThermometrieCarbon):
    SPI_CHANNEL = ADS1219.CHANNEL_AIN2_AIN3


class AttrsPT1000(ThermometriePT1000):
    SPI_CHANNEL = ADS1219.CHANNEL_AIN0_AIN1


def get_attrs(carbon):
    assert isinstance(carbon, bool)
    if carbon:
        return AttrsCarbon
    return AttrsPT1000


class OnewireBox:
    """
    DS18 blue heater box
    """

    def __init__(self, pin=Pin(PIN_DS18_TEMP)):
        assert isinstance(pin, Pin)
        ow = OneWire(pin)
        self._dx18x20 = DS18X20(ow)

    def scan(self):
        roms = self._dx18x20.scan()
        if len(roms) == 0:
            return None
        assert len(roms) <= 1, "Maximum one sensor expected"
        return ubinascii.hexlify(roms[0]).decode("ascii")

    def read_temp_C(self, ident):
        rom = ubinascii.unhexlify(ident)
        self._dx18x20.resolution(rom=rom, bits=12)
        self._dx18x20.convert_temp(rom=rom)
        # conversion takes up to 750ms
        time.sleep(0.8)
        return self._dx18x20.read_temp_C(rom)


class OnewireInsert(OnewireBox):
    """
    DS18 located in the insert and connected using the green Fischer cable.
    The blue heater box may power on/off this DS18.
    """

    def __init__(self):
        super().__init__(pin=Pin(PIN_DS18_ID))
        self.DS18_PWR = Pin(PIN_DS18_PWD, Pin.OUT_PP)
        self.DS18_SHORT = Pin(PIN_DS18_SHORT, Pin.OUT_PP)
        self._set_power(on=False)

    def _set_power(self, on):
        isinstance(on, bool)
        self.DS18_PWR.value(on)
        self.DS18_SHORT.value(not on)

    def scan(self):
        self._set_power(on=True)
        # Empirical value: 100us works, so 1ms might be safe
        # Usuing 0.001s, sometimes the id could not be read
        # Using 0.01s this negative effect has gone.
        # time.sleep(0.001)
        time.sleep(0.005)
        onewire_id = OnewireBox.scan(self)
        self._set_power(on=False)
        return onewire_id

    def read_temp_C(self, ident):
        raise Exception("Not supported (would be easy to implement...)")


class TemperatureInsert:
    def __init__(self, i2c):
        self.short_carb = Pin(PIN_SHORT_CARB, Pin.OUT_PP)
        self.short_pt1000 = Pin(PIN_SHORT_PT1000, Pin.OUT_PP)

        # https://www.ti.com/lit/ds/symlink/ads1219.pdf?ts=1629640067880&ref_url=https%253A%252F%252Fwww.ti.com%252Fproduct%252FADS1219
        #  ADS1219 4-Channel, 1-kSPS, 24-Bit, Delta-Sigma ADC With I2C Interface

        #   MCP4725 12-Bit Digital-to-Analog Converter with EEPROM Memory in SOT-23-6

        # ADC24
        # I2C(scl=Pin('X9'), sda=Pin('X10'), freq=400000)
        self.dataready = Pin(PIN_ADS1219_DRDY, Pin.IN)
        self.reset = Pin(PIN_ADS1219_RESET, Pin.OUT_PP)
        # active low, deshalb auf 1
        self.reset.value(1)
        self.adc = ADS1219(i2c)
        # try:
        #     self.adc = ADS1219(i2c)
        # except OSError as ex:
        #     if ex.args[0] != errno.ETIMEDOUT:
        #         raise
        #     self.adc = None

        self.adc.set_conversion_mode(ADS1219.CM_SINGLE)
        self.adc.set_vref(ADS1219.VREF_EXTERNAL)
        self.adc.set_gain(ADS1219.GAIN_1X)  # GAIN_1X, GAIN_4X
        self.adc.set_data_rate(ADS1219.DR_20_SPS)  # DR_20_SPS -> 50 ms

        self.enable_thermometrie(enable=False)

    def enable_thermometrie(self, enable):
        assert isinstance(enable, bool)
        self.short_carb.value(not enable)
        self.short_pt1000.value(not enable)

    def read_resistance_OHM(self, carbon):
        attrs = get_attrs(carbon=carbon)
        self.adc.set_channel(channel=attrs.SPI_CHANNEL)
        return self.adc.read_data_signed() * attrs.factor_adc_to_OHM()


class Heater:
    ADC_MAX = 2 ** 16 - 1

    def __init__(self, i2c):
        # DAC8571 16-BIT, LOW POWER, VOLTAGE OUTPUT, I2C INTERFACE DIGITAL-TO-ANALOG CONVERTER
        #
        # https://youtu.be/BvIQ0b2gUFs
        #
        # https://www.kernelconfig.io/config_ti_dac5571
        #  Driver for the Texas Instruments
        #    DAC5571, DAC6571, DAC7571, DAC5574, DAC6574, DAC7574, DAC5573,
        #    DAC6573, DAC7573, DAC8571, DAC8574
        # https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git/tree/drivers/iio/dac/ti-dac5571.c?h=v5.11.20
        #  Linux kernel driver in C
        self._dac = DAC8571(i2c)

    def set_power_off(self):
        self.set_power(0)

    def set_power_max(self):
        self.set_power(Heater.ADC_MAX)

    def set_power(self, power):
        assert not isinstance(power, bool)
        assert isinstance(power, int)
        assert 0 <= power <= Heater.ADC_MAX
        self._dac.write_dac(dac=power)


class Display:
    LINES = 5
    LINEHIGHT = 8 + 4

    def __init__(self, i2c, proxy):
        self._proxy = proxy
        self._sh1106 = SH1106_I2C(width=128, height=64, i2c=i2c, res=None, addr=0x3C)
        self._sh1106.sleep(False)
        self._sh1106.rotate(True, update=False)
        # 0..255  brigtness
        self._sh1106.contrast(255)
        self._sh1106.fill(0)

    def _line(self, i, text):
        assert 0 <= i < Display.LINES
        self._sh1106.text(text, 0, i * Display.LINEHIGHT, 1)

    def _clear(self):
        self._sh1106.fill(0)

    def _show(self):
        self._sh1106.show()

    def show_lines(self, lines, labber_driver=True):
        "This method will be called from the Labber Driver"
        if labber_driver:
            if self._proxy.defrost:
                # While the defrost switch is on, the defrost process controls the gui
                # and the labber is ignored
                return
        self._clear()
        for i, line in enumerate(lines):
            self._line(i, line)
        self._show()

    @staticmethod
    def lines_factory():
        return [
            "",
        ] * Display.LINES


class Proxy:
    ACTIVATE_WATCHDOG = True
    WATCHDOG_TIMEOUT_MS = 32767  # Max 32767

    def __init__(self):
        self._wdt = None
        if Proxy.ACTIVATE_WATCHDOG:
            assert Proxy.WATCHDOG_TIMEOUT_MS <= 2 ** 15 - 1, "WATCHDOG_TIMEOUT_MS too high!"
            self._wdt = WDT(timeout=Proxy.WATCHDOG_TIMEOUT_MS)
        self._defrost_pin = Pin(PIN_DEFROST, Pin.IN)
        # >>> i2c.scan()
        # [60]
        # 60=0x3C: OLED
        i2c_AD_DA = I2C(1, freq=40000)
        # >>> i2c.scan()
        # [72, 76, 98]
        # 72=0x48: ADS1291  TODO(hans) Why 48, should be 40!
        # 76=0x4C: DAC8571, DAC16
        # 98=0x62: MCP4725, DAC12
        i2c_OLED = I2C(2, freq=40000)
        self.display = Display(i2c=i2c_OLED, proxy=self)
        self.onewire_box = OnewireBox()
        self.onewire_insert = OnewireInsert()
        self.temperature_insert = TemperatureInsert(i2c=i2c_AD_DA)
        self.heater = Heater(i2c=i2c_AD_DA)
        self.defrost_process = DefrostProcess(self)

    def wdt_feed(self):
        if self._wdt:
            self._wdt.feed()

    @property
    def defrost(self):
        return not self._defrost_pin.value()

    def get_defrost(self):
        defrost = self.defrost
        if defrost:
            self.defrost_process.tick()
        self.wdt_feed()
        return defrost
