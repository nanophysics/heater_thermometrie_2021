import pathlib
import doctest
import hsm


class test_hsm(hsm.Statemachine):
    """
    This is a sample Statemachine as in figure 6.2 on page 170
    in 'Practical Statecharts in C/C++', ISBN 1-57820-110-1.
    """

    def __init__(self):
        super().__init__()
        self._foo = False

    def state_0(self, signal):
        'This is State "0"!'
        if signal == "E":
            raise hsm.StateChangeException(self.state_0_2_1_1)
        if signal == "I":
            raise hsm.StateChangeException(self.state_0)
        if signal == "J":
            raise hsm.IgnoreEventException()

    def state_0_1(self, signal):
        if signal == "A":
            raise hsm.StateChangeException(self.state_0_1)
        if signal == "C":
            raise hsm.StateChangeException(self.state_0_2)
        if signal == "D":
            raise hsm.StateChangeException(self.state_0)
        if signal == "E":
            raise hsm.StateChangeException(self.state_0_2_1_1)

    def state_0_1_1(self, signal):
        if signal == "G":
            raise hsm.StateChangeException(self.state_0_2_1_1)
        if signal == "H":
            if self._foo:
                self._foo = False

    def state_0_2(self, signal):
        if signal == "C":
            raise hsm.StateChangeException(self.state_0_1)
        if signal == "F":
            raise hsm.StateChangeException(self.state_0_1_1)

    def state_0_2_1(self, signal):
        if signal == "B":
            raise hsm.StateChangeException(self.state_0_2_1_1)
        if signal == "H":
            if not self._foo:
                self._foo = True
                raise hsm.StateChangeException(self.state_0_2_1)

    def state_0_2_1_1(self, signal):
        if signal == "C":
            raise hsm.StateChangeException(self.state_0_2_2)
        if signal == "D":
            raise hsm.StateChangeException(self.state_0_2_1)
        if signal == "G":
            raise hsm.StateChangeException(self.state_0)

    def state_0_2_2(self, signal):
        if signal == "B":
            raise hsm.IgnoreEventException()
        if signal == "G":
            raise hsm.StateChangeException(self.state_0_2_1)

    def entry_0(self, signal):
        pass

    def exit_0(self):
        pass

    def entry_0_1(self, signal):
        pass

    def exit_0_1(self):
        pass

    def entry_0_1_1(self, signal):
        pass

    init_ = state_0
    init_0 = state_0_1
    init_0_1 = state_0_1_1


def analyse():
    def func_log_main(strLine):
        print("Main: " + strLine)

    def func_log_sub(strLine):
        print("Sub:  " + strLine)

    sm = test_hsm()
    sm.func_log_main = func_log_main
    sm.func_log_sub = func_log_sub
    sm.reset()

    def test_entry_exit(sm, a, b, c, d, e):
        pass

    def test_transition(sm, signal, expect_state):
        sm.dispatch(signal)
        expect_state_name = expect_state.__name__[len("state_") :]
        assert expect_state_name == sm._state_actual

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

    # print(sm.doc())
    pathlib.Path("test_hsm_out.html").write_text(sm.doc())


def run_doctest():
    rc = doctest.testmod(hsm)
    if rc.failed > 0:
        raise Exception(rc)


if __name__ == "__main__":
    run_doctest()
    analyse()
