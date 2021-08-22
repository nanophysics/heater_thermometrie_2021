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
