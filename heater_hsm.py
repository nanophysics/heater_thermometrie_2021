from dataclasses import dataclass
import pathlib
import logging

from heater_thermometrie_2021_utils import EnumInsertConnected, EnumThermometrie
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
    This is a sample Statemachine as in figure 6.2 on page 170
    in 'Practical Statecharts in C/C++', ISBN 1-57820-110-1.
    """

    def __init__(self, hw: "HeaterWrapper"):
        super().__init__()
        assert hw.__class__.__name__ == "HeaterWrapper"
        self._hw = hw

    def state_off(self, signal):
        "Defrost off"
        # if isinstance(signal, SignalTick):
        #     raise hsm.StateChangeException(self.state_off)
        if isinstance(signal, SignalDefrostOnOff):
            if signal.on:
                raise hsm.StateChangeException(self.state_on)
        raise hsm.DontChangeStateException()

    def state_on(self, signal):
        "Defrost on"
        # if isinstance(signal, SignalTick):
        #     raise hsm.StateChangeException(self.state_on)
        if isinstance(signal, SignalDefrostOnOff):
            if not signal.on:
                raise hsm.StateChangeException(self.state_off)
        raise hsm.DontChangeStateException()

    init_ = state_off


class HeaterHsm(hsm.Statemachine):
    """
    This is a sample Statemachine as in figure 6.2 on page 170
    in 'Practical Statecharts in C/C++', ISBN 1-57820-110-1.
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

    def state_disconnected(self, signal):
        "The insert is not connected by the cable"
        if isinstance(signal, SignalInsertSerialChanged):
            if signal.is_connected:
                raise hsm.StateChangeException(self.state_connected)
        raise hsm.DontChangeStateException()

    def _handle_connected(self, signal):
        if isinstance(signal, SignalInsertSerialChanged):
            if not signal.is_connected:
                raise hsm.StateChangeException(self.state_disconnected)
        if isinstance(signal, SignalThermometrieOnOff):
            if signal.on:
                raise hsm.StateChangeException(self.state_connected_thermon)

    def state_connected(self, signal):
        "This insert is connected by the cable and the id was read successfully"
        self._handle_connected(signal)
        raise hsm.DontChangeStateException()

    def state_connected_thermoff(self, signal):
        "Thermometrie switch is off"
        self._handle_connected(signal)
        raise hsm.DontChangeStateException()

    def _handle_connected_thermon(self, signal):
        self._handle_connected(signal)
        if isinstance(signal, SignalThermometrieOnOff):
            if not signal.on:
                raise hsm.StateChangeException(self.state_connected_thermoff)

    def state_connected_thermon(self, signal):
        "Thermometrie switch is on"
        self._handle_connected_thermon(signal)
        raise hsm.DontChangeStateException()

    def state_connected_thermon_heatingoff(self, signal):
        "Heating off"
        pass

    def state_connected_thermon_heatingmanual(self, signal):
        "Heating manual"
        pass

    def state_connected_thermon_heatingcontrolled(self, signal):
        "Heating controlled by PID"
        pass

    def state_connected_thermon_heatingcontrolled_settling(self, signal):
        "The temperature is about to be settled"
        pass

    def state_connected_thermon_heatingcontrolled_settled(self, signal):
        "The temperature is settled"
        pass

    init_ = state_disconnected


def analyse():
    def func_log_main(msg):
        print("Main: " + msg)

    def func_log_sub(msg):
        print("Sub:  " + msg)

    header = heater_hsm()
    header.setLogger(func_log_main, func_log_sub)
    header.reset()

    defrost = defrost_hsm()
    defrost.setLogger(func_log_main, func_log_sub)
    defrost.reset()

    with pathlib.Path("thermometrie_hsm_out.html").open("w") as f:
        f.write(defrost.doc())
        f.write(header.doc())


if __name__ == "__main__":
    analyse()
