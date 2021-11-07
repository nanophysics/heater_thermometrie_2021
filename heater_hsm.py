from dataclasses import dataclass
import pathlib
import logging

from config_all import ONEWIRE_ID_INSERT_NOT_CONNECTED
from heater_driver_utils import (
    EnumHeating,
    EnumInsertConnected,
    EnumThermometrie,
    Quantity,
)
import hsm
from heater_pid_controller import PidController


logger = logging.getLogger("LabberDriver")


class SignalTick:
    def __repr__(self):
        return "SignalTick"


@dataclass
class SignalDefrostSwitchChanged:
    on: bool = None

    def __init__(self, on: bool) -> None:
        assert isinstance(on, bool)
        self.on = on


@dataclass
class SignalThermometrie:
    value: EnumThermometrie = None

    def __init__(self, value: EnumThermometrie) -> None:
        assert isinstance(value, EnumThermometrie)
        self.value = value

    @property
    def on(self):
        return self.value.on


@dataclass
class SignalHeating:
    value: EnumHeating = None

    def __init__(self, value: EnumHeating) -> None:
        assert isinstance(value, EnumHeating)
        self.value = value


@dataclass
class SignalInsertSerialChanged:
    onewire_id: str = None

    def __init__(self, onewire_id):
        assert isinstance(onewire_id, str)
        self.onewire_id = onewire_id

    @property
    def is_connected(self):
        return self.onewire_id != ONEWIRE_ID_INSERT_NOT_CONNECTED


class SignalHeaterSerialChanged(SignalInsertSerialChanged):
    pass


SIGNAL_TICK = SignalTick()


class HeaterHsm(hsm.Statemachine):  # pylint: disable=too-many-public-methods \# lic-methods
    """
    Statemachine Heater.
    """

    def __init__(self, hw: "HeaterWrapper"):
        super().__init__()
        assert hw.__class__.__name__ == "HeaterWrapper"
        self._hw = hw
        self.error_counter = 0
        self.controller = None
        self.last_outofrange_s = 0.0
        """
        Last time we have been outofrange
        """
        self.during_wait_temperature_and_settle = False
        """
        During ControlWriteTemperatureAndSettle this flag is set.
        """

    def wait_temperature_and_settle_start(self):
        self.during_wait_temperature_and_settle = True

    def wait_temperature_and_settle_over(self):
        self.error_counter = 0
        self.during_wait_temperature_and_settle = False

    @property
    def now_s(self) -> float:
        return self._hw.mpi.timebase.now_s

    def assert_valid_state(self) -> None:
        actual_meth = self.actual_meth()
        list_non_states = (HeaterHsm.state_connected, HeaterHsm.state_connected_thermon)
        if actual_meth in list_non_states:
            raise Exception(f"Entering non state '{actual_meth.__name__}'!")

    @property
    def get_labber_thermometrie(self):
        on = self._state_actual.startswith("connected_thermon")
        return EnumThermometrie.get_labber(on)

    @property
    def get_labber_insert_connected(self) -> str:
        connected = self._state_actual.startswith("connected")
        return EnumInsertConnected.get_labber(connected)

    def is_inrange(self):
        band_K = self._hw.get_quantity(Quantity.ControlWriteTemperatureToleranceBand)
        temperature_K = self._hw.get_quantity(Quantity.TemperatureReadonlyTemperatureCalibrated_K)
        temperature_should_K = self._hw.get_quantity(Quantity.ControlWriteTemperature)
        temperature_diff_K = temperature_K - temperature_should_K
        in_range = abs(temperature_diff_K) <= band_K
        return in_range

    def is_outofrange(self):
        return not self.is_inrange()

    def duration_inrange_s(self):
        return self.now_s - self.last_outofrange_s

    def is_settled(self):
        return self.duration_inrange_s() >= self._hw.get_quantity(Quantity.ControlWriteSettleTime)

    def get_heating_state(self, heating: EnumHeating):
        assert isinstance(heating, EnumHeating)
        if heating == EnumHeating.OFF:
            return self.state_connected_thermon_heatingoff
        if heating == EnumHeating.MANUAL:
            return self.state_connected_thermon_heatingmanual
        if heating == EnumHeating.CONTROLLED:
            return self.state_connected_thermon_heatingcontrolled
        raise AttributeError(f"Case {heating} not handled.")

    # def temperature_settled(self) -> bool:
    #     # TODO: Remove method
    #     self.expect_state(expected_meth=HeaterHsm.state_connected_thermon_heatingcontrolled)
    #     return self.settled # or self.timeout

    def state_disconnected(self, signal) -> None:
        """
        The insert is not connected by the cable.
        Poll periodically for onewire id of insert.
        """
        if isinstance(signal, SignalInsertSerialChanged):
            if signal.is_connected:
                raise hsm.StateChangeException(self.get_heating_state(heating=self._hw.get_quantity(Quantity.ControlWriteHeating)))
        raise hsm.DontChangeStateException()

    def state_connected(self, signal) -> None:
        """
        NONSTATE(entry=state_connected_thermon_xxx)
        The insert is connected by the cable and the id was read successfully.

        Periodically:
        -> If defrost_switch.is_on() => state_connected_thermon_heatingoff
        """
        if isinstance(signal, SignalInsertSerialChanged):
            if not signal.is_connected:
                raise hsm.StateChangeException(self.state_disconnected)
            if signal.serial == ONEWIRE_ID_INSERT_NOT_CONNECTED:
                raise hsm.StateChangeException(self.state_disconnected)

        if isinstance(signal, SignalThermometrie):
            if signal.on:
                raise hsm.StateChangeException(self.state_connected_thermon_heatingoff)
        if isinstance(signal, SignalDefrostSwitchChanged):
            if signal.on:
                raise hsm.StateChangeException(self.state_connected_thermon_defrost)
            raise hsm.DontChangeStateException()
        if isinstance(signal, SignalHeating):
            raise hsm.StateChangeException(self.get_heating_state(signal.value))

        if isinstance(signal, SignalTick):
            raise hsm.DontChangeStateException()

    def state_connected_thermoff(self, signal) -> None:
        """
        Thermometrie is off.
        No current in Carbon or PT1000 to avoid heating.

        A insert disconnect is NOT detected in this state.
        """

    def entry_connected_thermoff(self, signal) -> None:
        """
        heater.set_power(0)
        temperature_insert.enable_thermometrie(False)
        """
        self._hw.mpi.heater.set_power(power=False)
        self._hw.mpi.temperature_insert.enable_thermometrie(enable=False)

    def state_connected_thermon(self, signal) -> None:
        """
        NONSTATE(entry=state_connected_thermon_xxx)

        Thermometrie is on

        Periodically:
        - Observe two pins of the pyboard to see if insert was disconnected
        Periodically:
        - Read temperature_insert.get_voltage(carbon=True)
        - Read temperature_insert.get_voltage(carbon=False)
        - Calibration table -> temperature
        """
        if isinstance(signal, SignalThermometrie):
            if not signal.on:
                raise hsm.StateChangeException(self.state_connected_thermoff)

        in_range = self.is_inrange()
        if not in_range:
            self.last_outofrange_s = self.now_s
            self.error_counter += 1

        # SETTLED or TIMEOUT
        # if self.settled or self.timeout:
        # if self.timeout:
        #     if not in_range:
        #         self._hw.increment_error_counter()
        #     return

        # # Settling
        # # During settling, the error counter will never be incremented!
        # assert (not self.settled) and (not self.timeout)
        # if in_range:
        #     assert isinstance(self.settled_duration_s, float)
        #     if self.settled_duration_s > self._hw.get_quantity(Quantity.ControlWriteSettleTime):
        #         # During the settle time, the error counter should not be incremented
        #         self.settled = True
        #     return
        # # if now_s > self.time_start_s + self._hw.get_quantity(Quantity.ControlWriteTimeoutTime):
        # #     self._hw.increment_error_counter()
        # #     self.timeout = True

    def entry_connected_thermon(self, signal) -> None:
        """
        Read onewire id from insert.
        Load calibration tables for this insert.
        temperature_insert.enable_thermometrie(True)
        """
        self._hw.mpi.temperature_insert.enable_thermometrie(enable=False)

    def state_connected_thermon_heatingoff(self, signal) -> None:
        """
        Heating off
        """

    def entry_connected_thermon_heatingoff(self, signal) -> None:
        """
        heater.set_power(0)
        """

    def state_connected_thermon_heatingmanual(self, signal) -> None:
        """
        Heating manual
        """

    def entry_connected_thermon_heatingmanual(self, signal) -> None:
        """
        heater.set_power(Quantity.Power)
        """

    def state_connected_thermon_heatingcontrolled(self, signal) -> None:
        """
        Heating controlled by PI
        Periodically:
        - temperature -> PI controller -> power, 'in range' (Quantity.TemperatureToleranceBand)
        - heater.set_power(power)
        - if not 'in range':
          settle_time_start_s = time.now()
          Quantity.ErrorCounter += 1
        - settled = time.now() > settle_time_start_s + Quantiy.SettleTime
        """
        assert self.controller is not None

        setpoint_k = self._hw.get_quantity(Quantity.ControlWriteTemperature)
        temperature_calibrated_K = self._hw.get_quantity(Quantity.TemperatureReadonlyTemperatureCalibrated_K)

        self.controller.process(
            time_now_s=self.now_s,
            fSetpoint=setpoint_k,
            fSensorValue=temperature_calibrated_K,
            fLimitOutLow=0.0,
            fLimitOutHigh=100.0,
        )
        power100 = self.controller.fOutputValueLimited
        self._hw.set_quantity(Quantity.ControlWritePower100, power100)

        logger.debug(f"  setpoint={self.controller.fSetpoint:0.2f} K => calibrated_K={temperature_calibrated_K:0.2f} K => power={self.controller.fOutputValueLimited:0.2f} %")

    def entry_connected_thermon_heatingcontrolled(self, signal) -> None:
        """
        Initialize PI controller
        settle_time_start_s = time.now()
        """
        self.error_counter = 0
        setpoint_k = self._hw.get_quantity(Quantity.ControlWriteTemperature)
        self.controller = PidController(
            "insert",
            time_now_s=self.now_s,
            fSetpoint=setpoint_k,
            fKi=0.04,
            fKp=0.1,
            fKd=0.0,
        )

    def exit_connected_thermon_heatingcontrolled(self, signal) -> None:
        self.controller = None

    def state_connected_thermon_defrost(self, signal) -> None:
        """
        Heating controlled by the pyboard.

        We just display the state.

        The only way to got out of this state is
        - that the defrost switch is switched off.
        - disconnect the tail
        """
        if isinstance(signal, SignalDefrostSwitchChanged):
            if not signal.on:
                # Let a outer state take control
                return
        if isinstance(signal, SignalInsertSerialChanged):
            if not signal.is_connected:
                raise hsm.StateChangeException(self.state_disconnected)
        raise hsm.DontChangeStateException()

    init_ = state_disconnected
    init_state_connected = entry_connected_thermoff
    init_state_connected_thermon = state_connected_thermon_heatingoff


def analyse():
    def func_log_main(msg):
        pass

    def func_log_sub(msg):
        pass

    # pylint: disable=cyclic-import
    import heater_wrapper
    import micropython_proxy

    hw = heater_wrapper.HeaterWrapper(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
    header = HeaterHsm(hw)
    header.func_log_main = func_log_main
    header.func_log_sub = func_log_sub
    header.reset()

    with pathlib.Path("thermometrie_hsm_out.html").open("w") as f:
        f.write(header.doc())


if __name__ == "__main__":
    analyse()
