from dataclasses import dataclass
import pathlib
import logging

from heater_driver_utils import (
    EnumHeating,
    EnumInsertConnected,
    EnumThermometrie,
)
import hsm


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
    serial: str = None

    @property
    def is_connected(self):
        return self.serial is not None


class SignalHeaterSerialChanged(SignalInsertSerialChanged):
    pass


SIGNAL_TICK = SignalTick()


# class DefrostHsm(hsm.Statemachine):
#     """
#     This statemachine represents the defrost logic.
#     This logic is implemented in micropython, so defrosting may be done without labber.
#     """

#     def __init__(self, hw: "HeaterWrapper"):
#         super().__init__()
#         assert hw.__class__.__name__ == "HeaterWrapper"
#         self._hw = hw

#     def state_off(self, signal) -> None:
#         """
#         Defrost switch set to OFF
#         """
#         if isinstance(signal, SignalDefrostOnOff):
#             if signal.on:
#                 raise hsm.StateChangeException(self.state_on)
#         raise hsm.DontChangeStateException()

#     def state_on(self, signal) -> None:
#         """
#         NONSTATE(entry=state_on_heating)
#         Defrost switch set to ON.
#         """
#         assert False

#     def _handle_state_on(self, signal) -> None:
#         if isinstance(signal, SignalDefrostOnOff):
#             if not signal.on:
#                 raise hsm.StateChangeException(self.state_off)

#     def state_on_heating(self, signal) -> None:
#         """
#         The insert is still cold: heating is on.
#         """
#         self._handle_state_on(signal)

#         raise hsm.DontChangeStateException()

#     def state_on_warm(self, signal) -> None:
#         """
#         The insert is meanwhile warm: heating is off.
#         """

#     init_ = state_off


class HeaterHsm(hsm.Statemachine):
    """
    Statemachine Heater.
    """

    def __init__(self, hw: "HeaterWrapper"):
        super().__init__()
        assert hw.__class__.__name__ == "HeaterWrapper"
        self._hw = hw

    @property
    def get_labber_thermometrie(self):
        on = self._state_actual.startswith("connected_thermon")
        return EnumThermometrie.get_labber(on)

    @property
    def get_labber_insert_connected(self) -> str:
        connected = self._state_actual.startswith("connected")
        return EnumInsertConnected.get_labber(connected)

    def state_disconnected(self, signal) -> None:
        """
        The insert is not connected by the cable.
        Poll periodically for onewire id of insert.
        """
        if isinstance(signal, SignalInsertSerialChanged):
            if signal.is_connected:
                raise hsm.StateChangeException(self.state_connected_thermon)
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
        if isinstance(signal, SignalThermometrie):
            if signal.on:
                raise hsm.StateChangeException(self.state_connected_thermon)
        if isinstance(signal, SignalDefrostSwitchChanged):
            if signal.on:
                raise hsm.StateChangeException(self.state_connected_thermon_defrost)
            raise hsm.DontChangeStateException()
        if isinstance(signal, SignalHeating):

            def get_requested_state():
                if signal.value == EnumHeating.OFF:
                    return self.state_connected_thermon_heatingoff
                if signal.value == EnumHeating.MANUAL:
                    return self.state_connected_thermon_heatingmanual
                if signal.value == EnumHeating.CONTROLLED:
                    return self.state_connected_thermon_heatingcontrolled
                raise AttributeError(f"Case {signal.value} not handled.")

            raise hsm.StateChangeException(get_requested_state())

        if isinstance(signal, SignalTick):
            # def get_requested_state():
            #     if self._hw.get_quantity(Quantity.DefrostSwitchOnBox):
            #         return self.state_connected_thermon_defrost
            #     heating = self._hw.get_quantity(Quantity.Heating)
            #     if heating == EnumHeating.DEFROST:
            #         return self.state_connected_thermon_defrost
            #     if heating == EnumHeating.OFF:
            #         return self.state_connected_thermon_heatingoff
            #     if heating == EnumHeating.MANUAL:
            #         return self.state_connected_thermon_heatingmanual
            #     if heating == EnumHeating.CONTROLLED:
            #         return self.state_connected_thermon_heatingoff
            #     raise AttributeError(f"Case {heating.name} not handled.")

            # requested_state = get_requested_state()
            # if requested_state != self.actual_meth():
            #     raise hsm.StateChangeException(requested_state)
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
        self._hw.mpi.fe.proxy.heater.set_power(power=False)
        self._hw.mpi.fe.proxy.temperature_insert.enable_thermometrie(enable=False)

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

    def entry_connected_thermon(self, signal) -> None:
        """
        Read onewire id from insert.
        Load calibration tables for this insert.
        temperature_insert.enable_thermometrie(True)
        """
        self._hw.mpi.fe.proxy.temperature_insert.enable_thermometrie(enable=False)

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

    def entry_connected_thermon_heatingcontrolled(self, signal) -> None:
        """
        Initialize PI controller
        settle_time_start_s = time.now()
        """

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
