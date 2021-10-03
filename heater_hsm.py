from dataclasses import dataclass
import pathlib

import hsm


class SignalTick:
    def __repr__(self):
        return "SignalTick"


@dataclass
class SignalDefrostOnOff:
    on: bool = None


@dataclass
class SignalTailSerialChanged:
    serial: str = None

    @property
    def is_connected(self):
        return self.serial is not None

class SignalHeaterSerialChanged(SignalTailSerialChanged):
    pass

SIGNAL_TICK = SignalTick()


class DefrostHsm(hsm.Statemachine):
    """
    This is a sample Statemachine as in figure 6.2 on page 170
    in 'Practical Statecharts in C/C++', ISBN 1-57820-110-1.
    """

    def __init__(self):
        super().__init__()

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

    def __init__(self):
        super().__init__()

    def state_disconnected(self, signal):
        "The insert is not connected by the cable"
        if isinstance(signal, SignalTick):
            raise hsm.StateChangeException(self.state_connected)
        if isinstance(signal, SignalTailSerialChanged):
            if signal.is_connected:
                raise hsm.StateChangeException(self.state_connected)
        raise hsm.DontChangeStateException()

    def state_connected(self, signal):
        "This insert is connected by the cable and the id was read successfully"
        if isinstance(signal, SignalTick):
            raise hsm.StateChangeException(self.state_connected)
        if isinstance(signal, SignalTailSerialChanged):
            if not signal.is_connected:
                raise hsm.StateChangeException(self.state_disconnected)
        raise hsm.DontChangeStateException()

    def state_connected_thermoff(self, signal):
        "Thermometrie switch is off"
        pass

    def state_connected_thermon(self, signal):
        "Thermometrie switch is on"
        pass

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
