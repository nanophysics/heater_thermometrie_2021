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
from heater_pid_params import HeaterPidParams


logger = logging.getLogger("LabberDriver")

HEATING_POWER_MAX_W = 3.3  # max power for powersupply 0.22 A, might change later if not enough


@dataclass
class SignalDefrostSwitchChanged:
    defrost_on: bool = None

    def __init__(self, defrost_on: bool) -> None:
        assert isinstance(defrost_on, bool)
        self.defrost_on = defrost_on


@dataclass
class SignalInsertSerialChanged:
    onewire_id: str = None

    def __init__(self, onewire_id):
        assert isinstance(onewire_id, str)
        self.onewire_id = onewire_id

    @property
    def is_connected(self):
        return self.onewire_id != ONEWIRE_ID_INSERT_NOT_CONNECTED


class SignalTick:
    def __repr__(self):
        return "SignalTick"


SIGNAL_TICK = SignalTick()


class SignalHeaterSerialChanged(SignalInsertSerialChanged):
    pass


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
        self.last_outofrange_s = self.now_s
        """
        Last time we have been outofrange
        """
        self.during_wait_temperature_and_settle = False
        """
        During ControlWriteTemperatureAndSettle_K this flag is set.
        """

    def sim_reset_error_counter(self):
        self.error_counter = 0

    def reset_outofrange_s(self):
        self.last_outofrange_s = self.now_s
        self.error_counter = 0

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
    def get_labber_insert_connected(self) -> str:
        connected = self._state_actual.startswith("connected")
        return EnumInsertConnected.get_labber(connected)

    def is_inrange(self):
        band_K = self._hw.get_quantity(Quantity.ControlWriteTemperatureToleranceBand_K)
        temperature_K = self._hw.get_quantity(Quantity.TemperatureReadonlyTemperatureCalibrated_K)
        temperature_should_K = self._hw.get_quantity(Quantity.ControlWriteTemperature_K)
        temperature_diff_K = temperature_K - temperature_should_K
        in_range = abs(temperature_diff_K) <= band_K
        return in_range

    def is_outofrange(self):
        return not self.is_inrange()

    def duration_inrange_s(self):
        return self.now_s - self.last_outofrange_s

    def is_settled(self) -> bool:
        return self.duration_inrange_s() >= self._hw.get_quantity(Quantity.ControlWriteSettleTime_S)

    def get_heating_state(self, heating: EnumHeating = None):
        if heating is None:
            heating = self._hw.get_quantity(Quantity.ControlWriteHeating)
        assert isinstance(heating, EnumHeating)
        if heating.eq(EnumHeating.OFF):
            return self.state_connected_thermon_heatingoff
        if heating.eq(EnumHeating.MANUAL):
            return self.state_connected_thermon_heatingmanual
        if heating.eq(EnumHeating.CONTROLLED):
            return self.state_connected_thermon_heatingcontrolled
        raise AttributeError(f"Case {heating} not handled.")

    def state_disconnected(self, signal) -> None:
        """
        The insert is NOT connected by the cable.

        Periodically:

        -> if insert connected ==> state_connected_thermoff
        """
        if isinstance(signal, SignalInsertSerialChanged):
            if signal.is_connected:
                raise hsm.StateChangeException(self.state_connected_thermoff)
        raise hsm.DontChangeStateException()

    def state_connected(self, signal) -> None:
        """
        NONSTATE(entry=state_connected_thermoff)
        The insert is connected by the cable and the onewire_id was read successfully.

        Periodically:

        -> If insert removed => state_disconnected
        -> If defrost_switch.is_on() => state_connected_thermon_defrost
        """
        if isinstance(signal, SignalInsertSerialChanged):
            if not signal.is_connected:
                raise hsm.StateChangeException(self.state_disconnected)
            raise hsm.DontChangeStateException()

        if isinstance(signal, SignalDefrostSwitchChanged):
            if signal.defrost_on:
                raise hsm.StateChangeException(self.state_connected_thermon_defrost)
            raise hsm.DontChangeStateException()

        if isinstance(signal, SignalTick):
            raise hsm.DontChangeStateException()

    def state_connected_thermoff(self, signal) -> None:
        """
        Thermometrie is off.
        No current in Carbon or PT1000 to avoid heating.

        A insert disconnect is NOT detected in this state.
        """
        thermometrie = self._hw.get_quantity(Quantity.ControlWriteThermometrie)
        if thermometrie.eq(EnumThermometrie.ON):
            raise hsm.StateChangeException(self.get_heating_state())

    def entry_connected_thermoff(self, signal) -> None:
        """
        set_power_W(0.0)
        temperature_insert.enable_thermometrie(enable=False)
        """
        self._hw.set_power_W(power_W=0.0)
        self._hw.mpi.temperature_insert.enable_thermometrie(enable=False)

    def state_connected_thermon(self, signal) -> None:
        """
        NONSTATE(entry=state_connected_thermon_heatingoff)

        Thermometrie is on

        Periodically:

        -> If termometrie off ==> state_connected_thermoff
        -> Poll the PT1000 to detect disconnection of the tail (Y1/PIN_CONNECTED_PT1000)
        -> if not in_range ==> Increment 'error_counter', update 'last_outofrange_s'

        Done in 'heater_wrapper':
        -> Read temperature_insert.get_voltage(carbon=True)
        -> Read temperature_insert.get_voltage(carbon=False)
        -> Calibration table -> temperature
        """
        thermometrie = self._hw.get_quantity(Quantity.ControlWriteThermometrie)
        if thermometrie.eq(EnumThermometrie.OFF):
            raise hsm.StateChangeException(self.state_connected_thermoff)

        if not self._hw.mpi.get_pt1000_connected():
            raise hsm.StateChangeException(self.state_disconnected)

        in_range = self.is_inrange()
        if not in_range:
            self.last_outofrange_s = self.now_s
            self.error_counter += 1

        new_heating_state = self.get_heating_state()
        if not self.is_state(new_heating_state):
            raise hsm.StateChangeException(new_heating_state)

    def entry_connected_thermon(self, signal) -> None:
        """
        - temperature_insert.enable_thermometrie(True)
        - Reset 'error_counter'
        - Reset 'last_outofrange_s'
        """
        self._hw.mpi.temperature_insert.enable_thermometrie(enable=True)
        self.reset_outofrange_s()

    def state_connected_thermon_heatingoff(self, signal) -> None:
        """
        Heating off
        """

    def entry_connected_thermon_heatingoff(self, signal) -> None:
        """
        set_power_W(0.0)
        """
        self._hw.set_power_W(power_W=0.0)

    def state_connected_thermon_heatingmanual(self, signal) -> None:
        """
        Heating manual
        """

    def entry_connected_thermon_heatingmanual(self, signal) -> None:
        """
        ? heater.set_power(Quantity.Power)
        """

    def exit_connected_thermon_heatingmanual(self) -> None:
        """
        set_power_W(0.0)
        """
        self._hw.set_power_W(power_W=0.0)

    def state_connected_thermon_heatingcontrolled(self, signal) -> None:
        """
        Heating controlled by PI

        Periodically:
        - temperature -> PI controller -> power, 'in range' (Quantity.TemperatureToleranceBand)
        - set_power_W(power)
        """
        assert self.controller is not None

        setpoint_k = self._hw.get_quantity(Quantity.ControlWriteTemperature_K)
        temperature_K = self._hw.get_quantity(Quantity.TemperatureReadonlyTemperatureCalibrated_K)

        params = HeaterPidParams(setpoint_k=setpoint_k)

        self.controller.fKp = params.fKp
        self.controller.fKi = params.fKi
        self.controller.fKd = params.fKd

        self.controller.process(
            time_now_s=self.now_s,
            fSetpoint=setpoint_k,
            fSensorValue=temperature_K,
            fLimitOutLow=0.0,
            fLimitOutHigh=HEATING_POWER_MAX_W,
            bAllowDecreaseI=True,  # ? todo was ist das
            bAllowIncreaseI=True,  # ? todo was ist das
        )
        power_W = self.controller.fOutputValueLimited
        logger.debug(f"  setpoint={self.controller.fSetpoint:0.2f} K => calibrated_K={temperature_K:0.2f} K => power={self.controller.fOutputValueLimited:0.2f} %")
        logger.warning(f"  setpoint={self.controller.fSetpoint:0.3f} K => temperature_K={temperature_K:0.3f} K => power={power_W:0.3f} W   controller fI ={self.controller.fI:0.2f}")
        self._hw.set_power_W(power_W=power_W)

    def entry_connected_thermon_heatingcontrolled(self, signal) -> None:
        """
        Initialize PI controller
        - Reset 'error_counter'
        - Initialize PID
        """
        self.error_counter = 0
        setpoint_k = self._hw.get_quantity(Quantity.ControlWriteTemperature_K)
        # temperature_K = self._hw.get_quantity(Quantity.TemperatureReadonlyTemperatureCalibrated_K)

        params = HeaterPidParams(setpoint_k=setpoint_k)

        self.controller = PidController(
            "insert",
            time_now_s=self.now_s,
            fSetpoint=setpoint_k,
            # fKi=0.04,
            # fKp=0.1,
            # fKp=7.7,
            # fKi=0.323,
            # fKd=32.65,
            fKp=params.fKp,
            fKi=params.fKi,
            fKd=params.fKd,
            # fSensorValue=temperature_K,
            fSensorValue=setpoint_k,  # damit wird der i Anteil auf 0 initialisiert
            fOutputValue=0.0,
        )

    def exit_connected_thermon_heatingcontrolled(self) -> None:
        self.controller = None

    def state_connected_thermon_defrost(self, signal) -> None:
        """
        Heating controlled by the pyboard.

        We just display the state.

        Periodically:

        -> Defrost switch off ==> see 'state_connected_thermon'
        -> insert removed ==> state_disconnected
        -> Otherwise stay in this state
        """
        if isinstance(signal, SignalDefrostSwitchChanged):
            if not signal.defrost_on:
                # Let a outer state take control
                return
        if isinstance(signal, SignalInsertSerialChanged):
            if not signal.is_connected:
                raise hsm.StateChangeException(self.state_disconnected)
        raise hsm.DontChangeStateException()

    init_ = state_disconnected
    init_state_connected = state_connected_thermoff
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
