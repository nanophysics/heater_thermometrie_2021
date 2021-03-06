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

    ControlWriteHeating = "Control Heating / Mode"
    ControlWriteExpert = "Expert"
    ControlWriteLogging = "Control Mode / Logging"
    ControlWriteThermometrie = "Control Heating / Thermometrie"
    ControlWriteGreenLED = "Green LED"
    ControlWritePower_W = "Control Heating / set power (mode manual)"
    ControlWriteTemperature_K = "Control Heating / set temperature (mode controlled)"
    ControlWriteTemperatureAndSettle_K = "Control Heating / set temperature and settle (mode controlled)"
    ControlWriteTemperatureToleranceBand_K = "Control Heating / temperature tolerance band (plus minus)"
    ControlWriteSettleTime_S = "Control Heating / settle time (mode controlled)"
    ControlWriteTimeoutTime_S = "Control Heating / timeout time (mode controlled)"
    StatusReadTemperatureBox_C = "Temperature HeaterBox / Temperature_C"
    StatusReadSerialNumberHeater = "Status Heater / Serial Number Heater"
    StatusReadSerialNumberInsertHidden = "SerialNumberInsertHidden"
    StatusReadSerialNumberInsert = "Status Heater / Serial Number Insert"
    StatusReadDefrostSwitchOnBox = "Status Heater / Defrost - Switch on box"
    StatusReadDefrostUserInteraction = "Status Heater / Defrost - User interaction"
    StatusReadInsertConnected = "Status Insert / Insert Connected"
    StatusReadErrorCounter = "Status Heater / Error counter"
    StatusReadSettled = "Status Heater / Settled (expert)"
    TemperatureReadonlyResistanceCarbon_OHM = "Temperature Resistance / Carbon_Ohm (expert)"
    TemperatureReadonlyResistancePT1000_OHM = "Temperature Resistance / PT1000_Ohm (expert)"
    TemperatureReadonlyTemperatureCarbon_K = "Temperature Temperature / Carbon_K (expert)"
    TemperatureReadonlyTemperaturePT1000_K = "Temperature Temperature / PT1000_K (expert)"
    TemperatureReadonlyTemperatureCalibrated_K = "Temperature Temperature / Temperature_K"
