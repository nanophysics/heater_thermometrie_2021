import pathlib
import hsm


class test_hsm(hsm.Statemachine):
    """
    This is a sample Statemachine as in figure 6.2 on page 170
    in 'Practical Statecharts in C/C++', ISBN 1-57820-110-1.
    """

    def __init__(self):
        super().__init__()
        self.foo = False

    def state_0(self, objSignal):
        'This is State "0"!'
        if objSignal == "E":
            raise hsm.StateChangeException(self.state_0_2_1_1)
        if objSignal == "I":
            raise hsm.StateChangeException(self.state_0)
        if objSignal == "J":
            raise hsm.IgnoreEventException()

    def state_0_1(self, objSignal):
        if objSignal == "A":
            raise hsm.StateChangeException(self.state_0_1)
        if objSignal == "C":
            raise hsm.StateChangeException(self.state_0_2)
        if objSignal == "D":
            raise hsm.StateChangeException(self.state_0)
        if objSignal == "E":
            raise hsm.StateChangeException(self.state_0_2_1_1)

    def state_0_1_1(self, objSignal):
        if objSignal == "G":
            raise hsm.StateChangeException(self.state_0_2_1_1)
        if objSignal == "H":
            if self.foo:
                self.foo = False

    def state_0_2(self, objSignal):
        if objSignal == "C":
            raise hsm.StateChangeException(self.state_0_1)
        if objSignal == "F":
            raise hsm.StateChangeException(self.state_0_1_1)

    def state_0_2_1(self, objSignal):
        if objSignal == "B":
            raise hsm.StateChangeException(self.state_0_2_1_1)
        if objSignal == "H":
            if not self.foo:
                self.foo = True
                raise hsm.StateChangeException(self.state_0_2_1)

    def state_0_2_1_1(self, objSignal):
        if objSignal == "C":
            raise hsm.StateChangeException(self.state_0_2_2)
        if objSignal == "D":
            raise hsm.StateChangeException(self.state_0_2_1)
        if objSignal == "G":
            raise hsm.StateChangeException(self.state_0)

    def state_0_2_2(self, objSignal):
        if objSignal == "B":
            raise hsm.IgnoreEventException()
        if objSignal == "G":
            raise hsm.StateChangeException(self.state_0_2_1)

    def entry_0(self, objSignal):
        pass

    def exit_0(self):
        pass

    def entry_0_1(self, objSignal):
        pass

    def exit_0_1(self):
        pass

    def entry_0_1_1(self, objSignal):
        pass

    init_ = state_0
    init_0 = state_0_1
    init_0_1 = state_0_1_1


def analyse():
    def funcLogMain(strLine):
        print("Main: " + strLine)

    def funcLogSub(strLine):
        print("Sub:  " + strLine)

    sm = test_hsm()
    sm.setLogger(funcLogMain, funcLogSub)
    sm.reset()

    def test_entry_exit(sm, a, b, c, d, e):
        pass

    def test_transition(sm, objSignal, expectState):
        sm.dispatch(objSignal)
        expectStateName = expectState.__name__[len("state_") :]
        assert expectStateName == sm.private_strStateActual

    # TRIPTEST_ASSERT(hsm_Statemachine.state == sm.state_011)
    test_entry_exit(sm, 1, 0, 1, 0, 1)

    test_transition(sm, "G", sm.state_0_2_1_1)
    test_entry_exit(sm, 0, 0, 0, 1, 0)

    test_transition(sm, "F", sm.state_0_1_1)
    test_entry_exit(sm, 0, 0, 1, 0, 1)

    test_transition(sm, "E", sm.state_0_2_1_1)
    test_entry_exit(sm, 0, 0, 0, 1, 0)

    test_transition(sm, "C", sm.state_0_2_2)
    test_entry_exit(sm, 0, 0, 0, 0, 0)

    test_transition(sm, "B", sm.state_0_2_2)
    test_entry_exit(sm, 0, 0, 0, 0, 0)

    test_transition(sm, "E", sm.state_0_2_1_1)
    test_entry_exit(sm, 1, 1, 0, 0, 0)

    test_transition(sm, "D", sm.state_0_2_1)
    test_entry_exit(sm, 0, 0, 0, 0, 0)

    test_transition(sm, "C", sm.state_0_1_1)
    test_entry_exit(sm, 0, 0, 1, 0, 1)

    test_transition(sm, "A", sm.state_0_1_1)
    test_entry_exit(sm, 0, 0, 1, 1, 1)

    test_transition(sm, "I", sm.state_0_1_1)
    test_entry_exit(sm, 1, 1, 1, 1, 1)

    test_transition(sm, "G", sm.state_0_2_1_1)
    test_entry_exit(sm, 0, 0, 0, 1, 0)

    test_transition(sm, "I", sm.state_0_1_1)
    test_entry_exit(sm, 1, 1, 1, 0, 1)

    test_transition(sm, "J", sm.state_0_1_1)
    test_entry_exit(sm, 0, 0, 0, 0, 0)

    print("\nIf you got here, the statemachine seems to work ok!\n\n")

    # print(sm.doc)
    pathlib.Path("test_hsm_out.html").write_text(sm.doc)

def run_doctest():
    import doctest, hsm

    rc = doctest.testmod(hsm)
    if rc.failed > 0:
        raise Exception(rc)

if __name__ == "__main__":
    run_doctest()
    analyse()
