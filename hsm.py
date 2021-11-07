import io
import re
import types
import inspect

REGEX_SPACES = re.compile(r"^(?P<spaces>.*?)(\S(.*)$)", re.M)
NOT_INITIALIZED_YET = "NOT-INITIALIZED-YET"


class StateChangeException(Exception):
    def __init__(self, meth_new_state):
        Exception.__init__(self, f"New state is: {meth_new_state.__name__}")
        self.meth_new_state = meth_new_state


class IgnoreSignalException(Exception):
    pass


class DontChangeStateException(Exception):
    pass


class BadStatemachineException(Exception):
    def __init__(self, strMsg):
        Exception.__init__(self, strMsg)


class Statemachine:
    def __init__(self):
        self._list_state_names: list = None
        self._list_init_names: list = None
        self._list_entry_names: list = None
        self._list_exit_names: list = None
        self._dict_init_state = {}

        def log_main(msg):
            print(msg)

        def log_sub(msg):
            print(f"  {msg}")

        def log_state_change(signal, handling_state, state_before, new_state):
            print(f"  {repr(signal)}: {handling_state}: {state_before} -> {new_state}")

        self.func_log_main = log_main
        self.func_log_sub = log_sub
        self.func_state_change = log_state_change
        self._state_actual: str = NOT_INITIALIZED_YET

    @property
    def state(self) -> str:
        assert isinstance(self._state_actual, str)
        return self._state_actual

    def actual_meth(self):
        meth = getattr(self.__class__, "state_" + self._state_actual)
        assert isinstance(meth, types.FunctionType)
        return meth

    def is_state(self, expected_meth):
        if inspect.ismethod(expected_meth):
            expected_meth = expected_meth.__func__
        assert isinstance(expected_meth, types.FunctionType)
        return expected_meth == self.actual_meth()

    def expect_state(self, expected_meth):
        assert isinstance(expected_meth, types.FunctionType)
        actual_meth = self.actual_meth()
        if expected_meth != actual_meth:
            raise Exception(f"Expected state '{expected_meth.__name__}' but got '{actual_meth.__name__}'!")

    def dispatch(self, signal):
        state_before = self._state_actual

        try:
            self.func_log_main(f"{repr(signal)}: was handled by 'state_{self._state_actual}'")
            handling_state = self._state_actual
            while True:
                meth = getattr(self, "state_" + handling_state)
                self.func_log_sub(f"  calling '{meth.__name__}({signal})'")
                meth(signal)
                i = handling_state.rfind("_")
                if i < 0:
                    raise Exception(f"  Signal '{repr(signal)}' was not handled by state 'state_{state_before}'!")
                    # print('Empty Transition!')
                    # return
                handling_state = handling_state[:i]
            return
        except DontChangeStateException as e:
            self.func_log_sub("  No state change!")
            return
        except IgnoreSignalException as e:
            self.func_log_sub("  Empty Transition!")
            return
        except StateChangeException as e:
            self.func_log_sub(f"{repr(signal)}: was handled by 'state_{handling_state}'")
            # Evaluate init-state
            new_state = e.meth_new_state.__name__.replace("state_", "")
            if self._state_actual != new_state:
                if self.func_state_change is not None:
                    self.func_state_change(
                        signal=signal,
                        handling_state=handling_state,
                        state_before=state_before,
                        new_state=new_state,
                    )
            init_state = self.get_init_state(new_state)
            if init_state != new_state:
                self.func_log_sub(f"  Init-State for {new_state} is {init_state}.")
            self._state_actual = init_state

        # Call the exit/entry-actions
        self.call_exit_entry_actions(signal, state_before, init_state)

    def get_init_state(self, state):
        try:
            return self.get_init_state(self._dict_init_state[state])
        except KeyError as _e:
            return state

    def get_method_list(self, strType):
        results = []
        for name, value in inspect.getmembers(self, predicate=inspect.ismethod):
            if name.startswith(strType):
                results.append(name[len(strType) :])
        results.sort()
        return results

    def call_exit_entry_actions(self, signal, state_before, strStateAfter):
        list_state_before = state_before.split("_")
        list_state_after = strStateAfter.split("_")

        # Find toppest state
        i_toppest_state = 0
        for before, after in zip(list_state_before, list_state_after):
            if before != after:
                break
            i_toppest_state += 1

        # Call all Exit-Actions
        for i in range(len(list_state_before), i_toppest_state, -1):
            state = "_".join(list_state_before[:i])
            try:
                func_exit = getattr(self, "exit_" + state)
            except AttributeError as _e:
                pass
            else:
                self.func_log_sub(f"  Calling {func_exit.__name__}")
                func_exit()
        # Call all Entry-Actions
        for i in range(i_toppest_state, len(list_state_after)):
            state = "_".join(list_state_after[: i + 1])
            try:
                func_entry = getattr(self, "entry_" + state)
            except AttributeError as _e:
                pass
            else:
                self.func_log_sub(f"  Calling {func_entry.__name__}")
                func_entry(signal)

    def get_top_state_obsolete(self, list_state):
        top_state = None
        for state in list_state:
            if len(state.split("_")) == 1:
                top_state = state
        if top_state is None:
            raise BadStatemachineException("No Top State found")
        return top_state

    def consistency_check(self):
        for action, _list in (
            ("entry_", self._list_entry_names),
            ("exit_", self._list_exit_names),
        ):
            for entry in _list:
                try:
                    meth = getattr(self, "state_" + entry)
                except AttributeError as e:
                    raise BadStatemachineException(f"No corresponding 'state_{entry}()' for '{action}{entry}()'!") from e

    def reset(self):
        self._list_state_names = self.get_method_list("state_")
        self._list_init_names = self.get_method_list("init_")
        self._list_entry_names = self.get_method_list("entry_")
        self._list_exit_names = self.get_method_list("exit_")
        for init_state in self._list_init_names:
            objValue = getattr(self, "init_" + init_state)
            self._dict_init_state[init_state] = objValue.__name__[len("state_") :]

        # Find top state
        if "" not in self._dict_init_state:
            raise BadStatemachineException('Init-State on top-level is required but missing. Example "init_ = state_XYZ".')

        # Evaluate the init-state
        self._state_actual = self.get_init_state("")

        # Verify validity of the entry and exit actions
        self.consistency_check()

    def start(self):
        # Call the entry-actions
        # self.call_exit_entry_actions(self.top_state, self._state_actual)
        self.call_exit_entry_actions(None, "", self._state_actual)

    @staticmethod
    def _beautify_docstring(docstring):
        if docstring is None:
            return None
        docstring = docstring.replace("\r\n", "\n")
        lines = []
        for line in docstring.split("\n"):
            line = line.strip()
            if line == "":
                continue
            lines.append(line)
        if len(lines) == 0:
            return None
        return "<br>".join(lines)

    def get_docstring(self, methodname):
        docstring = inspect.getdoc(getattr(self, methodname))
        if docstring:
            return self._beautify_docstring(docstring)
        return None

    def get_hierarchy_(self, parent_state=""):
        list_level = []
        for state in self._list_state_names:
            if state.find(parent_state) != 0:
                continue
            if len(state.split("_")) == len(parent_state.split("_")) + 1:
                strName = state.split("_")[-1]
                list_level.append(
                    {
                        "fullname": state,
                        "name": strName,
                        "substates": self.get_hierarchy(state),
                    }
                )
                continue
        return list_level

    def get_hierarchy(self, parent_state=None):
        list_level = []
        for state in self._list_state_names:
            if not parent_state:
                if len(state.split("_")) == 1:
                    list_level.append((state, self.get_hierarchy(state)))
                continue
            if state.find(parent_state) != 0:
                continue
            if len(state.split("_")) != len(parent_state.split("_")) + 1:
                continue
            list_level.append((state, self.get_hierarchy(state)))
        return list_level

    def doc_state(self, state):
        f = io.StringIO()
        f.write('<table class="table_state">')
        f.write("  <tr>")
        text = state.split("_")[-1]
        f.write(f'    <td class="td_header" colSpan="3">{text}</td>')
        f.write("  </tr>")
        if state in self._list_init_names:
            init_state = self._dict_init_state[state]
            f.write('<TR class="tr_init">')
            f.write("  <TD></TD>")
            f.write('  <TD class="td_label">init</TD>')
            f.write(f'  <TD class="td_text">{init_state}</TD>')
            f.write("</TR>")
        if state in self._list_entry_names:
            docstring = self.get_docstring("entry_" + state)
            if docstring:
                f.write('<TR class="tr_entry">')
                f.write("  <TD></TD>")
                f.write('  <TD class="td_label">entry</TD>')
                f.write(f'  <TD class="td_text">{docstring}</TD>')
                f.write("</TR>")
        docstring = self.get_docstring(f"state_{state}")
        if docstring:
            f.write('<tr class="tr_comment">')
            f.write('  <td class="td_space">&nbsp;&nbsp;&nbsp;</td>')
            f.write('  <td class="td_label">comment</td>')
            f.write(f'  <td class="td_text">{docstring}</td>')
            f.write("</tr>")
        if state in self._list_exit_names:
            docstring = self.get_docstring("exit_" + state)
            if docstring:
                f.write('<TR class="tr_exit">')
                f.write("  <TD></TD>")
                f.write('  <TD class="td_label">exit</TD>')
                f.write(f'  <TD class="td_text">{docstring}</TD>')
                f.write("</TR>")
        if False:
            bShowSource = False
            if bShowSource:
                strSource = inspect.getsource(getattr(self, "state_" + state))
                if not strSource:
                    strSource = "&nbsp;"
                f.write(f'<td valign="top" height="100%"><pre class="small">{strSource}</pre></td>')
        return f.getvalue(), "</table>"

    def doc_state_recursive(self, list_level):
        f = io.StringIO()
        for state, list_state in list_level:
            state_begin, state_end = self.doc_state(state)
            state_sub = self.doc_state_recursive(list_state)
            f.write(state_begin)
            if state_sub:
                f.write('  <tr class="tr_sub">')
                f.write('    <td class="td_space">&nbsp;&nbsp;&nbsp;</td>')
                f.write('    <td class="td_substate" colSpan="2">')
                f.write(state_sub)
                f.write("    </td>")
                f.write("  </tr>")
            f.write(state_end)
        return f.getvalue()

    def doc(self):
        """
        Return a HTML-Page which describes the HSM
        """
        f = io.StringIO()
        f.write(html_header)
        docstring = self._beautify_docstring(self.__doc__)
        if docstring:
            f.write("<p>" + docstring + "</p><br>")
        list_level = self.get_hierarchy()
        s = self.doc_state_recursive(list_level)
        f.write(s)
        f.write("</body>\n")
        f.write("</html>\n")
        return f.getvalue()


html_header = """
<!DOCTYPE html>
<html lang="en">
  <head>
    <title>Hierarchical State Machine</title> 
    <meta http-equiv='content-type' content='text/html;charset=iso-8859-1'>
    <meta content='HSM by Maerki Informatik' name='description'>
    <style type='text/css'>
    <!--
    /*  common styles  */
    table.table_state {width: 100%; border-left: 2px solid #000000; border-right: 2px solid #000000; border-top: 0px solid #000000; border-bottom: 0px solid #000000}
    td {padding-left:3px; padding-right:3px}
    td.td_header {background-color: #EEEEEE; border-bottom: 1px solid #000000; border-top: 1px solid #000000; font-weight: bold}
    td.td_label {font-size: smaller; width: 1%; font-style: italic}
    td.td_text {font-size: smaller}
    td.td_space {width: 1%}
    td.td_substate {width: 100%}
    -->
    </style>
  </head>
  <body>
"""

# class Test_NoTopState(Statemachine):
#  '''
#    >>> sm = Test_NoTopState()
#    >>> sm.reset()
#    Traceback (most recent call last):
#    ...
#    BadStatemachineException: No Top State found
#  '''
#  def state_TopA_SubB(self, signal):
#    pass
#  init_ = state_TopA_SubB


class Test_UnmatchedEntryAction(Statemachine):
    """
    >>> sm = Test_UnmatchedEntryAction()
    >>> sm.reset()
    Traceback (most recent call last):
    ...
    BadStatemachineException: No corresponding 'state_TopA_SubB()' for 'entry_TopA_SubB()'!
    """

    def state_TopA(self, signal):
        pass

    def entry_TopA_SubB(self, signal):
        pass

    init_ = state_TopA


class Test_UnmatchedExitAction(Statemachine):
    """
    >>> sm = Test_UnmatchedExitAction()
    >>> sm.reset()
    Traceback (most recent call last):
    ...
    BadStatemachineException: No corresponding 'state_TopA_SubB()' for 'exit_TopA_SubB()'!
    """

    def state_TopA(self, signal):
        pass

    def exit_TopA_SubB(self):
        pass

    init_ = state_TopA


class Test_SimpleStatemachineTopStateHandlesSignal(Statemachine):
    """
    >>> sm = Test_SimpleStatemachineTopStateHandlesSignal()
    >>> sm.reset()
    >>> sm.dispatch('a')
    'a': was handled by 'state_TopA_SubA'
        calling 'state_TopA_SubA(a)'
        calling 'state_TopA(a)'
        No state change!
    """

    def state_TopA(self, signal):
        if signal == "a":
            raise DontChangeStateException

    def state_TopA_SubA(self, signal):
        if signal == "b":
            raise StateChangeException(self.state_TopA_SubA)

    init_ = state_TopA_SubA


class Test_SimpleStatemachine(Statemachine):
    """
    >>> sm = Test_SimpleStatemachine()
    >>> sm.reset()
    >>> sm.dispatch('a')
    'a': was handled by 'state_TopA'
        calling 'state_TopA(a)'
      'a': was handled by 'state_TopA'
      'a': TopA: TopA -> TopA_SubA
    >>> sm.dispatch('b')
    'b': was handled by 'state_TopA_SubA'
        calling 'state_TopA_SubA(b)'
      'b': was handled by 'state_TopA_SubA'
      'b': TopA_SubA: TopA_SubA -> TopA_SubB
        Calling entry_TopA_SubB
    >>> sm.dispatch('b')
    'b': was handled by 'state_TopA_SubB'
        calling 'state_TopA_SubB(b)'
        calling 'state_TopA(b)'
        Empty Transition!
    >>> sm.dispatch('a')
    'a': was handled by 'state_TopA_SubB'
        calling 'state_TopA_SubB(a)'
        calling 'state_TopA(a)'
      'a': was handled by 'state_TopA'
      'a': TopA: TopA_SubB -> TopA_SubA
        Calling exit_TopA_SubB
    """

    def state_TopA(self, signal):
        if signal == "a":
            raise StateChangeException(self.state_TopA_SubA)
        raise IgnoreSignalException()

    def state_TopA_SubA(self, signal):
        if signal == "b":
            raise StateChangeException(self.state_TopA_SubB)

    def state_TopA_SubB(self, signal):
        pass

    def exit_TopA_SubB(self):
        pass

    def entry_TopA_SubB(self, signal):
        pass

    init_ = state_TopA


class Test_StatemachineWithEntryExitActions(Statemachine):
    """
    >>> sm = Test_StatemachineWithEntryExitActions()
    >>> sm.reset()
    >>> sm.dispatch('r')
    'r': was handled by 'state_TopA'
        calling 'state_TopA(r)'
      'r': was handled by 'state_TopA'
      'r': TopA: TopA -> TopC
        Calling exit_TopA
        Calling entry_TopC
    >>> sm.dispatch('s')
    's': was handled by 'state_TopC'
        calling 'state_TopC(s)'
      's': was handled by 'state_TopC'
      's': TopC: TopC -> TopB_SubA_SubsubA
        Calling exit_TopC
        Calling entry_TopB
        Calling entry_TopB_SubA
        Calling entry_TopB_SubA_SubsubA
    >>> sm.dispatch('t')
    't': was handled by 'state_TopB_SubA_SubsubA'
        calling 'state_TopB_SubA_SubsubA(t)'
      't': was handled by 'state_TopB_SubA_SubsubA'
      't': TopB_SubA_SubsubA: TopB_SubA_SubsubA -> TopC
        Calling exit_TopB_SubA_SubsubA
        Calling exit_TopB_SubA
        Calling exit_TopB
        Calling entry_TopC

    Traceback (most recent call last):
    ...
    Exception: Signal c was not handled!
    """

    def state_TopA(self, signal):
        raise StateChangeException(self.state_TopC)

    def exit_TopA(self):
        pass

    def state_TopB(self, signal):
        pass

    def entry_TopB(self, signal):
        pass

    def exit_TopB(self):
        pass

    def state_TopB_SubA(self, signal):
        pass

    def entry_TopB_SubA(self, signal):
        pass

    def exit_TopB_SubA(self):
        pass

    def state_TopB_SubA_SubsubA(self, signal):
        raise StateChangeException(self.state_TopC)

    def entry_TopB_SubA_SubsubA(self, signal):
        pass

    def exit_TopB_SubA_SubsubA(self):
        pass

    def state_TopC(self, signal):
        raise StateChangeException(self.state_TopB_SubA_SubsubA)

    def entry_TopC(self, signal):
        pass

    def exit_TopC(self):
        pass

    init_ = state_TopA


def run_doctest():
    import doctest

    rc = doctest.testmod(name="hsm")
    if rc.failed > 0:
        raise Exception(rc)


if __name__ == "__main__":
    run_doctest()
