"""
  This runs on Micropython and on the PC!
"""


class Thermometrie:
    U3V = 3.33333333
    ZEROCELSIUS_K = 273.15
    CURRENT_A = 10e-6
    R31_44_OHM = "do be defined by derived class"

    @classmethod
    def ia_gain(cls):
        return 1.0 + 50000.0 / cls.R31_44_OHM

    @classmethod
    def adc24_factor(cls):
        return cls.U3V / (2.0 ** 23) / cls.ia_gain()

    @classmethod
    def factor_adc_to_OHM(cls):
        return cls.adc24_factor() / cls.CURRENT_A

    @staticmethod
    def get_thermometrie(carbon):
        if carbon:
            return ThermometrieCarbon
        return ThermometriePT1000


class ThermometrieCarbon(Thermometrie):
    IS_CARBON = True
    NAME = "carbon"
    R31_44_OHM = 100.0  # R31


class ThermometriePT1000(Thermometrie):
    IS_CARBON = False
    NAME = "pt1000"
    R31_44_OHM = 200.0  # R44

    PT1000_30C_OHM = 1116.73
    "https://www.temperaturmesstechnik.de/fileadmin/user_upload/pdf/tmh_pt1000_tabelle.pdf"

    @staticmethod
    def temperature_C(resistance_OHM):
        return (resistance_OHM - 1000.0) * 30.0 / (ThermometriePT1000.PT1000_30C_OHM - 1000.0)

    @staticmethod
    def resistance_OHM(temperature_K):
        temperature_C = temperature_K - Thermometrie.ZEROCELSIUS_K
        return 1000.0 + temperature_C * (ThermometriePT1000.PT1000_30C_OHM - 1000.0) / 30.0
