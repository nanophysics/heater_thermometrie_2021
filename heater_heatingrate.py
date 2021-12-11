"""
Heating Power Curve
Measurement on prototype insert_2019

The heater_thermometrie_2021 has a special characteristics.
Very fine resolution at low heating power.
The measured values here are measured by
Peter with the heater_thermometrie_2021 prototype
and insert_2019 prototype.
"""
import numpy


class HeatingCurve:
    """
    # todo: implement somehow.
    max power for powersupply 0.22 A, might change later if not enough
    """

    ADC_MIN = 0
    ADC_MAX = 2 ** 16 - 1
    _CURVE_W = [
        0.00e0,
        6.15e-13,
        7.59e-13,
        8.28e-13,
        7.89e-13,
        5.68e-13,
        1.26e-12,
        5.77e-13,
        9.35e-13,
        1.49e-12,
        2.16e-12,
        2.09e-12,
        2.81e-12,
        2.65e-12,
        3.21e-12,
        3.51e-12,
        4.67e-12,
        5.79e-12,
        7.23e-12,
        9.19e-12,
        1.23e-11,
        1.41e-11,
        1.91e-11,
        2.75e-11,
        3.50e-11,
        4.77e-11,
        6.25e-11,
        9.72e-11,
        1.30e-10,
        1.91e-10,
        2.96e-10,
        4.57e-10,
        7.25e-10,
        1.17e-9,
        2.02e-9,
        3.71e-9,
        7.38e-9,
        1.54e-8,
        3.49e-8,
        8.53e-8,
        2.20e-7,
        6.09e-7,
        1.77e-6,
        5.01e-6,
        1.33e-5,
        3.28e-5,
        7.28e-5,
        1.45e-4,
        2.66e-4,
        4.55e-4,
        6.14e-4,
        1.19e-3,
        1.82e-3,
        2.68e-3,
        3.88e-3,
        5.52e-3,
        7.73e-3,
        1.07e-2,
        1.46e-2,
        1.97e-2,
        2.63e-2,
        3.51e-2,
        4.64e-2,
        6.08e-2,
        7.94e-2,
        1.03e-1,
        1.34e-1,
        1.73e-1,
        2.24e-1,
        2.88e-1,
        3.70e-1,
        4.74e-1,
        6.06e-1,
        7.73e-1,
        9.84e-1,
        1.25e0,
        1.59e0,
        2.02e0,
        2.56e0,
        3.24e0,
        4.11e0,
        5.08e0,
    ]
    _CURVE_DAC = [
        0,
        7,
        7,
        8,
        9,
        10,
        12,
        13,
        15,
        16,
        18,
        21,
        23,
        26,
        29,
        33,
        37,
        41,
        46,
        52,
        58,
        66,
        74,
        83,
        93,
        104,
        117,
        131,
        147,
        165,
        185,
        207,
        233,
        261,
        293,
        328,
        369,
        413,
        464,
        521,
        584,
        655,
        735,
        825,
        926,
        1039,
        1165,
        1308,
        1467,
        1646,
        1847,
        2072,
        2325,
        2609,
        2927,
        3285,
        3685,
        4135,
        4640,
        5206,
        5841,
        6554,
        7353,
        8250,
        9257,
        10387,
        11654,
        13076,
        14671,
        16462,
        18470,
        20724,
        23253,
        26090,
        29273,
        32845,
        36853,
        41350,
        46395,
        52056,
        58408,
        65535,
    ]

    def __init__(self, heating_power_max_W: float):
        assert isinstance(heating_power_max_W, float)
        self._heating_power_max_W = heating_power_max_W
        assert len(HeatingCurve._CURVE_W) == len(HeatingCurve._CURVE_DAC)

    def get_DAC(self, power_W: float) -> float:
        """
        Given power_w,  interpolates the value of 16bit-DAC.
        """
        assert isinstance(power_W, float)
        dac = numpy.interp(power_W, HeatingCurve._CURVE_W, HeatingCurve._CURVE_DAC)
        assert isinstance(dac, float)
        dac = int(dac)
        assert isinstance(dac, int)
        dac = min(max(dac, HeatingCurve.ADC_MIN), HeatingCurve.ADC_MAX)
        return dac
