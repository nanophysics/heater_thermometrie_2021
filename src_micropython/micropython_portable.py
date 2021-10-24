"""
  This runs on Micropython and on the PC!
"""


# @dataclass
# class SensorAttributes:
#     carbon: bool
#     text: str
#     current_a: float
#     quantity_resistance: Quantity
#     quantity_temperature: Quantity

# attributes_carbon = SensorAttributes(carbon=True, text="carbon", current_a=Thermometrie.CURRENT_A_CARBON, quantity_resistance=Quantity.TemperatureReadonlyResistanceCarbon, quantity_temperature=Quantity.TemperatureReadonlyTemperatureCarbon)
class Thermometrie:
    U3V = 3.33333333
    PTC30K_OHM = 1116.73
    "https://www.temperaturmesstechnik.de/fileadmin/user_upload/pdf/tmh_pt1000_tabelle.pdf"
    R31_44_OHM = "do be defined by derived class"
    CURRENT_A = "do be defined by derived class"

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
    CURRENT_A = 10e-6
    R31_44_OHM = 100.0  # R31


class ThermometriePT1000(Thermometrie):
    IS_CARBON = False
    NAME = "ptc1000"
    CURRENT_A = 10e-6
    R31_44_OHM = 200.0  # R44
    # IA_GAIN = 1.0 + 50000.0 / R31_44_OHM
    # ADC24_FACTOR = U3V / (2.0 ** 23) / IA_GAIN

    @staticmethod
    def temperature_C(resistance_OHM):
        return (resistance_OHM - 1000.0) * 30.0 / (Thermometrie.PTC30K_OHM - 1000.0)
