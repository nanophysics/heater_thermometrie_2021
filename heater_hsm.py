import pathlib

import hsm

class SignalTick:
    pass

SIGNAL_TICK = SignalTick()
class DefrostHsm(hsm.Statemachine):
    """
    This is a sample Statemachine as in figure 6.2 on page 170
    in 'Practical Statecharts in C/C++', ISBN 1-57820-110-1.
    """

    def __init__(self):
        super().__init__()

    def state_off(self, objSignal):
        "Defrost off"
        pass

    def state_on(self, objSignal):
        "Defrost on"
        pass

    init_ = state_off


class HeaterHsm(hsm.Statemachine):
    """
    This is a sample Statemachine as in figure 6.2 on page 170
    in 'Practical Statecharts in C/C++', ISBN 1-57820-110-1.
    """

    def __init__(self):
        super().__init__()

    def state_disconnected(self, objSignal):
        "The insert is not connected by the cable"
        pass

    def state_connected(self, objSignal):
        "This insert is connected by the cable and the id was read successfully"
        pass

    def state_connected_termoff(self, objSignal):
        "Thermometrie switch is off"
        pass

    def state_connected_termon(self, objSignal):
        "Thermometrie switch is on"
        pass

    def state_connected_termon_heatingoff(self, objSignal):
        "Heating off"
        pass

    def state_connected_termon_heatingmanual(self, objSignal):
        "Heating manual"
        pass

    def state_connected_termon_heatingcontrolled(self, objSignal):
        "Heating controlled by PID"
        pass

    def state_connected_termon_heatingcontrolled_settling(self, objSignal):
        "The temperature is about to be settled"
        pass

    def state_connected_termon_heatingcontrolled_settled(self, objSignal):
        "The temperature is settled"
        pass

    init_ = state_disconnected


def analyse():
    def funcLogMain(strLine):
        print("Main: " + strLine)

    def funcLogSub(strLine):
        print("Sub:  " + strLine)

    header = heater_hsm()
    header.setLogger(funcLogMain, funcLogSub)
    header.reset()

    defrost = defrost_hsm()
    defrost.setLogger(funcLogMain, funcLogSub)
    defrost.reset()

    with pathlib.Path("thermometrie_hsm_out.html").open("w") as f:
        f.write(defrost.doc())
        f.write(header.doc())


if __name__ == "__main__":
    analyse()
