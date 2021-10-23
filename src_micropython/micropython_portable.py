"""
  This runs on Micropython and on the PC!
"""


class Thermometrie:
    CURRENT_A_CARBON = 10e-6
    CURRENT_A_PT1000 = 10e-6
    U3V = 3.33333333
    R31_OHM = 100.0
    R44_OHM = 200.0
    IA_GAIN_CARBON = 1.0 + 50000.0 / R31_OHM
    IA_GAIN_PT1000 = 1.0 + 50000.0 / R44_OHM
    ADC24_FACTOR_CARBON = U3V / (2.0 ** 23) / IA_GAIN_CARBON
    ADC24_FACTOR_PT1000 = U3V / (2.0 ** 23) / IA_GAIN_PT1000
    PTC30K_OHM = 1116.73
    "https://www.temperaturmesstechnik.de/fileadmin/user_upload/pdf/tmh_pt1000_tabelle.pdf"

    @staticmethod
    def ptc1000_temperature_C(resistance_OHM):
        return (resistance_OHM - 1000.0) * 30.0 / (Thermometrie.PTC30K_OHM - 1000.0)

    @staticmethod
    def factor_adc_to_OHM(carbon):
        if carbon:
            return Thermometrie.ADC24_FACTOR_CARBON / Thermometrie.CURRENT_A_CARBON
        return Thermometrie.ADC24_FACTOR_PT1000 / Thermometrie.CURRENT_A_PT1000
