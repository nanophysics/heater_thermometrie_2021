from dataclasses import dataclass
import pathlib
import logging

from heater_driver_utils import EnumInsertConnected, EnumThermometrie
import hsm


logger = logging.getLogger("LabberDriver")


class SignalTick:
    def __repr__(self):
        return "SignalTick"


@dataclass
class SignalDefrostOnOff:
    on: bool = None


@dataclass
class SignalThermometrieOnOff:
    value: EnumThermometrie = None

    def __init__(self, value) -> None:
        assert isinstance(value, EnumThermometrie)
        self.value = value

    @property
    def on(self):
        return self.value.on


@dataclass
class SignalInsertSerialChanged:
    serial: str = None

    @property
    def is_connected(self):
        return self.serial is not None


class SignalHeaterSerialChanged(SignalInsertSerialChanged):
    pass


SIGNAL_TICK = SignalTick()


class DefrostHsm(hsm.Statemachine):
    """
    This statemachine represents the defrost switch.
    """

    def __init__(self, hw: "HeaterWrapper"):
        super().__init__()
        assert hw.__class__.__name__ == "HeaterWrapper"
        self._hw = hw

    def state_off(self, signal) -> None:
        """
        Defrost switch set to OFF
        """
        # if isinstance(signal, SignalTick):
        #     raise hsm.StateChangeException(self.state_off)
        if isinstance(signal, SignalDefrostOnOff):
            if signal.on:
                raise hsm.StateChangeException(self.state_on)
        raise hsm.DontChangeStateException()

    def state_on(self, signal) -> None:
        """
        Defrost switch set to ON.
        """
        # if isinstance(signal, SignalTick):
        #     raise hsm.StateChangeException(self.state_on)
        if isinstance(signal, SignalDefrostOnOff):
            if not signal.on:
                raise hsm.StateChangeException(self.state_off)
        raise hsm.DontChangeStateException()

    def state_on_heating(self, signal) -> None:
        """
        The insert is still cold: heating is on.
        """

    def state_on_warm(self, signal) -> None:
        """
        The insert is meanwhile warm: heating is off.
        """

    init_ = state_off


class HeaterHsm(hsm.Statemachine):
    """
    Statemachine Heater
    TODO: When may be polled for the Insert-ID?
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
        The insert is not connected by the cable
        """
        if isinstance(signal, SignalInsertSerialChanged):
            if signal.is_connected:
                raise hsm.StateChangeException(self.state_connected)
        raise hsm.DontChangeStateException()

    def _handle_connected(self, signal) -> None:
        if isinstance(signal, SignalInsertSerialChanged):
            if not signal.is_connected:
                raise hsm.StateChangeException(self.state_disconnected)
        if isinstance(signal, SignalThermometrieOnOff):
            if signal.on:
                raise hsm.StateChangeException(self.state_connected_thermon)

    def state_connected(self, signal) -> None:
        """
        This insert is connected by the cable and the id was read successfully
        """
        self._handle_connected(signal)
        raise hsm.DontChangeStateException()

    def state_connected_thermoff(self, signal) -> None:
        """
        Thermometrie is off
        TODO:
        bei OFF keinen Strom durch Messwiderstände und keine Temperatur zurück geben und nicht heizen, nicht regeln.
        SHORT_CARB.value(0)
        SHORT_PT1000.value(0)
        """
        self._handle_connected(signal)
        raise hsm.DontChangeStateException()

    def _handle_connected_thermon(self, signal) -> None:
        self._handle_connected(signal)
        if isinstance(signal, SignalThermometrieOnOff):
            if not signal.on:
                raise hsm.StateChangeException(self.state_connected_thermoff)

    def state_connected_thermon(self, signal) -> None:
        """
        Thermometrie is on
        """
        self._handle_connected_thermon(signal)
        raise hsm.DontChangeStateException()

    def state_connected_thermon_heatingoff(self, signal) -> None:
        """
        Heating off
        """

    def state_connected_thermon_heatingmanual(self, signal) -> None:
        """
        Heating manual
        """

    def state_connected_thermon_heatingcontrolled(self, signal) -> None:
        """
        Heating controlled by PID
        """

    def state_connected_thermon_heatingcontrolled_settling(self, signal) -> None:
        """
        The temperature is about to be settled
        """

    def state_connected_thermon_heatingcontrolled_settled(self, signal) -> None:
        """
        The temperature is settled
        """

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

    defrost = DefrostHsm(hw)
    defrost.func_log_main = func_log_main
    defrost.func_log_sub = func_log_sub
    defrost.reset()

    with pathlib.Path("thermometrie_hsm_out.html").open("w") as f:
        f.write(defrost.doc())
        f.write(header.doc())


if __name__ == "__main__":
    analyse()
