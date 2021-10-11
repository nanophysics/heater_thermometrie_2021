from dataclasses import dataclass
import pathlib
import logging

import config_all

import heater_hsm
from micropython_proxy import HWTYPE_HEATER_THERMOMETRIE_2021
from micropython_interface import MicropythonInterface
from heater_driver_utils import (
    Quantity,
    QuantityNotFoundException,
    EnumLogging,
    EnumHeating,
    EnumExpert,
    EnumThermometrie,
)

logger = logging.getLogger("LabberDriver")

DIRECTORY_OF_THIS_FILE = pathlib.Path(__file__).absolute().parent


@dataclass
class NotInitialized:
    pass


NOT_INITIALIZED = NotInitialized()


class HeaterWrapper:
    def __init__(self, hwserial):
        self.dict_values = {}
        self.mpi = MicropythonInterface(hwserial)

        self.insert_config = config_all.ConfigInsert.load_config(config_all.ONEWIRE_ID_UNDEFINED)
        self.heater_2021_config = config_all.ConfigHeater2021.load_config(serial=self.mpi.heater_thermometrie_2021_serial)
        logger.info(f"{HWTYPE_HEATER_THERMOMETRIE_2021} connected: {self.heater_2021_config}")
        self.dict_values[Quantity.SerialNumberHeater] = repr(self.heater_2021_config)

        self.hsm_heater = heater_hsm.HeaterHsm(self)
        # self.hsm_defrost = heater_hsm.DefrostHsm(self)

        self.filename_values = DIRECTORY_OF_THIS_FILE / f"Values-{self.mpi.heater_thermometrie_2021_serial}.txt"

        def init_hsm(hsm):
            def log_main(msg):
                logger.debug(f"*** {msg}")

            def log_sub(msg):
                logger.debug(f"     {msg}")

            def log_state_change(signal, handling_state, state_before, new_state):
                logger.info(f"{repr(signal)}")
                logger.info(f"  {handling_state}: {state_before} -> {new_state}")

            hsm.func_log_main = log_main
            hsm.func_log_sub = log_sub
            hsm.func_state_change = log_state_change
            hsm.reset()

        init_hsm(self.hsm_heater)
        # init_hsm(self.hsm_defrost, "defrost")

        self.mpi.init()

        id_box = self.mpi.onewire_box.scan()
        id_box_expected = self.heater_2021_config.ONEWIRE_ID_HEATER
        if id_box != id_box_expected:
            logger.warning(f"Expected onewire_id of heater '{id_box_expected}' but got '{id_box}")

        # Read all initial values from the pyboard
        self.dict_values[Quantity.Heating] = EnumHeating.OFF
        self.tick()

    def close(self):
        self.mpi.close()

    def tick(self):
        # self.dict_values[Quantity.Temperature] = self.mpi.temperature_insert.get_voltage(carbon=True)
        # self.dict_values[Quantity.Temperature] = self.mpi.temperature_insert.get_voltage(carbon=False)
        self.dict_values[Quantity.Power] = 0.53
        self.dict_values[Quantity.Thermometrie] = True

        def defrost_switch_changed(on: str) -> str:
            self.hsm_heater.dispatch(heater_hsm.SignalDefrostSwitchChanged(on=on))
            return on

        self._set_value(
            Quantity.DefrostSwitchOnBox,
            self.mpi.defrost_switch.is_on(),
            defrost_switch_changed
        )

        def insert_onewire_id_changed(onewire_id: str) -> str:
            self.hsm_heater.dispatch(heater_hsm.SignalInsertSerialChanged(serial=onewire_id))
            self.insert_config = config_all.ConfigInsert.load_config(onewire_id=onewire_id)
            self.dict_values[Quantity.SerialNumberInsert] = repr(self.insert_config)
            return onewire_id

        self.mpi.onewire_insert.set_power(on=True)
        self._set_value(
            Quantity.SerialNumberInsertHidden,
            self.mpi.onewire_insert.scan(),
            insert_onewire_id_changed,
        )
        self.mpi.onewire_insert.set_power(on=False)

        # self.hsm_defrost.dispatch(heater_hsm.SIGNAL_TICK)
        self.hsm_heater.dispatch(heater_hsm.SIGNAL_TICK)

    def get_quantity(self, quantity: Quantity):
        assert isinstance(quantity, Quantity)
        return self.get_value(quantity.value)

    def get_value(self, name: str):
        assert isinstance(name, str)
        quantity = Quantity(name)
        if quantity == Quantity.Thermometrie:
            return self.hsm_heater.get_labber_thermometrie
        if quantity == Quantity.InsertConnected:
            return self.hsm_heater.get_labber_insert_connected

        if quantity == Quantity.TemperatureAndWait:
            # TemperatureAndWait is stored as Temperature
            quantity = Quantity.Temperature

        try:
            return self.dict_values[quantity]
        except KeyError as e:
            raise QuantityNotFoundException(name) from e

    def set_value(self, name: str, value):
        quantity = Quantity(name)
        if quantity == Quantity.Heating:
            value_new = EnumHeating(value)
            self.hsm_heater.dispatch(heater_hsm.SignalHeating(value=value_new))
            return value
        if quantity == Quantity.Expert:
            value_new = EnumExpert(value)
            self.dict_values[quantity] = value_new
            return value
        if quantity == Quantity.Logging:
            value_new = EnumLogging(value)
            self.dict_values[quantity] = value_new
            value_new.setLevel()
            return value
        if quantity == Quantity.Thermometrie:
            value_new = EnumThermometrie(value)
            self.hsm_heater.dispatch(heater_hsm.SignalThermometrie(value=value_new))
            return value
        if quantity == Quantity.GreenLED:
            value_new = bool(value)
            self.dict_values[quantity] = value_new
            return value
        if quantity in (Quantity.Temperature, Quantity.TemperatureAndWait):
            # This is the same temperature
            self.dict_values[Quantity.Temperature] = value
            return value

        if quantity in (
            Quantity.Power,
            Quantity.TemperatureBox,
            Quantity.TemperatureToleranceBand,
            Quantity.SettleTime,
            Quantity.TimeoutTime,
        ):
            self.dict_values[quantity] = value
            return value
        raise QuantityNotFoundException(name)

    def _set_value(self, quantity: Quantity, value, func=None) -> bool:
        """
        Returns true if value changes
        """
        before = self.dict_values.get(quantity, NOT_INITIALIZED)
        after = self.dict_values[quantity] = value
        value_changed = before != after
        if value_changed and func is not None:
            func(value)
        return value_changed
