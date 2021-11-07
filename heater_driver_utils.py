import enum
import logging

logger = logging.getLogger("LabberDriver")


class QuantityNotFoundException(Exception):
    pass


class EnumMixin:
    def eq(self, other):
        assert isinstance(other, type(self))
        return self == other

    @classmethod
    def all_text(cls):
        return ", ".join(sorted([f'"{d.name}"' for d in cls]))

    @classmethod
    def get_exception(cls, configuration: str, value: str):
        assert isinstance(configuration, str)
        assert isinstance(value, str)
        err = f'{configuration}: Unkown "{value}". Expect one of {cls.all_text()}!'
        try:
            return cls[value]
        except KeyError as e:
            raise Exception(err) from e


class EnumHeating(EnumMixin, enum.Enum):
    OFF = "off"
    MANUAL = "manual"
    CONTROLLED = "controlled"
    # DEFROST = "defrost"


class EnumExpert(EnumMixin, enum.Enum):
    SIMPLE = "simple"
    EXPERT = "expert"


class EnumLogging(EnumMixin, enum.Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"

    def setLevel(self):
        level = {
            EnumLogging.DEBUG: logging.DEBUG,
            EnumLogging.INFO: logging.INFO,
            EnumLogging.WARNING: logging.WARNING,
        }[self]
        logger.info(f"Set Logging Level to '{self.name}'")
        logger.setLevel(level)


class EnumThermometrie(EnumMixin, enum.Enum):
    ON = "on"
    OFF = "off"

    @property
    def on(self):
        return self == EnumThermometrie.ON

    @staticmethod
    def get_labber(on) -> str:
        assert isinstance(on, bool)
        if on:
            return EnumThermometrie.ON.value
        return EnumThermometrie.OFF.value


class EnumInsertConnected(EnumMixin, enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTED = "connected"

    @staticmethod
    def get_labber(connected) -> str:
        assert isinstance(connected, bool)
        if connected:
            return EnumInsertConnected.CONNECTED.value
        return EnumInsertConnected.DISCONNECTED.value


class Quantity(EnumMixin, enum.Enum):
    """
    Readable name => value as in 'heater_thermometrie_2021.ini'
    """

    ControlWriteHeating = "Heating"
    ControlWriteExpert = "Expert"
    ControlWriteLogging = "Logging"
    ControlWriteThermometrie = "Thermometrie"
    ControlWriteGreenLED = "Green LED"
    ControlWritePower100 = "power"
    ControlWriteTemperature = "temperature"
    ControlWriteTemperatureAndSettle = "temperature and settle"
    TemperatureReadonlyTemperatureBox = "Temperature Box"
    ControlWriteTemperatureToleranceBand = "temperature tolerance band"
    ControlWriteSettleTime = "settle time"
    ControlWriteTimeoutTime = "timeout time"
    StatusReadSerialNumberHeater = "Serial Number Heater"
    StatusReadSerialNumberInsertHidden = "SerialNumberInsertHidden"
    StatusReadSerialNumberInsert = "Serial Number Insert"
    StatusReadDefrostSwitchOnBox = "Defrost - Switch on box"
    StatusReadDefrostUserInteraction = "Defrost - User interaction"
    StatusReadInsertConnected = "Connected"
    StatusReadErrorCounter = "Error counter"
    StatusReadSettled = "Settled"
    TemperatureReadonlyResistanceCarbon_OHM = "Carbon"
    TemperatureReadonlyResistancePT1000_OHM = "PT1000_K"
    TemperatureReadonlyTemperatureCarbon_K = "Carbon calibrated"
    TemperatureReadonlyTemperaturePT1000_K = "PT1000_K calibrated"
    TemperatureReadonlyTemperatureCalibrated_K = "calibrated"
