import io
import re
import inspect

REGEX_SPACES = re.compile(r"^(?P<spaces>.*?)(\S(.*)$)", re.M)


class StateChangeException(Exception):
    def __init__(self, meth_new_state):
        Exception.__init__(self, f"New state is: {meth_new_state.__name__}")
        self.meth_new_state = meth_new_state


class IgnoreEventException(Exception):
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
        self._list_entry_names : list = None
        self._list_exit_names : list = None
        self._dict_init_state = {}

        def log_main(strLine):
            print(strLine)

        def log_sub(strLine):
            print(f"  {strLine}")

        self.func_log_main = log_main
        self.func_log_sub = log_sub
        self._state_actual = "NOT-INITIALIZED-YET"

    @property
    def state(self):
        return self._state_actual

    def dispatch(self, signal):
        strStateBefore = self._state_actual

        try:
            self.func_log_main(f"{repr(signal)}: will be handled by {self._state_actual}")
            self.func_log_sub(f'  calling state "state_{strStateBefore}({signal})"')
            handling_state = self._state_actual
            while True:
                meth = getattr(self, "state_" + handling_state)
                meth(signal)
                i = handling_state.rfind("_")
                if i < 0:
                    raise Exception(f"Signal {signal} was not handled!")
                    # print('Empty Transition!')
                    # return
                handling_state = handling_state[:i]
            return
        except DontChangeStateException as e:
            self.func_log_sub("  No state change!")
            return
        except IgnoreEventException as e:
            self.func_log_sub("  Empty Transition!")
            return
        except StateChangeException as e:
            self.func_log_sub(f"{signal}: was handled by state_{handling_state}")
            # Evaluate init-state
            new_state = e.meth_new_state.__name__.replace("state_", "")
            init_state = self.get_init_state(new_state)
            if init_state != new_state:
                self.func_log_sub(f"  Init-State for {new_state} is {init_state}.")
            self._state_actual = init_state

        # Call the exit/entry-actions
        self.call_exit_entry_actions(signal, strStateBefore, init_state)

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

    def call_exit_entry_actions(self, signal, strStateBefore, strStateAfter):
        list_state_before = strStateBefore.split("_")
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

        return

    def get_top_state_obsolete(self, list_state):
        top_state = None
        for state in list_state:
            if len(state.split("_")) == 1:
                top_state = state
        if top_state == None:
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
                    raise BadStatemachineException(f"No corresponding state_{entry}() for {action}{entry}()!") from e

    def reset(self):
        self._list_state_names = self.get_method_list("state_")
        self._list_init_names = self.get_method_list("init_")
        self._list_entry_names = self.get_method_list("entry_")
        self._list_exit_names = self.get_method_list("exit_")
        for init_state in self._list_init_names:
            objValue = getattr(self, "init_" + init_state)
            self._dict_init_state[init_state] = objValue.__name__[len("state_") :]

        # Find top state
        if not "" in self._dict_init_state:
            raise BadStatemachineException('Init-State on top-level is required but missing. Example "init_ = state_XYZ".')

        # Evaluate the init-state
        self._state_actual = self.get_init_state("")

        # Verify validity of the entry and exit actions
        self.consistency_check()

    def start(self):
        # Call the entry-actions
        # self.call_exit_entry_actions(self.top_state, self._state_actual)
        self.call_exit_entry_actions(None, "", self._state_actual)

    def _beautify_docstring(self, docstring):
        docstring = "\n" + docstring.replace("\r\n", "\n")
        docstring = docstring.replace("\r", "")
        # remove empty lines at the begin
        objMatch = REGEX_SPACES.search(docstring)
        if objMatch:
            strSpaces = objMatch.groupdict(0)["spaces"]
            docstring = docstring.replace("\n" + strSpaces, "\n")
        docstring = docstring.strip()
        docstring = docstring.replace("\n", "<br>\n")
        return docstring.replace(" ", "&nbsp;")

    def get_docstring(self, methodname):
        docstring = inspect.getdoc(getattr(self, methodname))
        if docstring:
            # docstring = docstring.strip().replace('\n', '<br>')
            return self._beautify_docstring(docstring)
        return ""

    def get_hierarchy_(self, parent_state=""):
        listLevel = []
        for state in self._list_state_names:
            if state.find(parent_state) != 0:
                continue
            if len(state.split("_")) == len(parent_state.split("_")) + 1:
                strName = state.split("_")[-1]
                listLevel.append(
                    {
                        "fullname": state,
                        "name": strName,
                        "substates": self.get_hierarchy(state),
                    }
                )
                continue
        return listLevel

    def get_hierarchy(self, parent_state=None):
        listLevel = []
        for state in self._list_state_names:
            if not parent_state:
                if len(state.split("_")) == 1:
                    listLevel.append((state, self.get_hierarchy(state)))
                continue
            if state.find(parent_state) != 0:
                continue
            if len(state.split("_")) != len(parent_state.split("_")) + 1:
                continue
            listLevel.append((state, self.get_hierarchy(state)))
        return listLevel

    def doc_state(self, state):
        f = io.StringIO()
        f.write('<table class="table_state">')
        f.write("  <tr>")
        text = state.split("_")[-1]
        f.write(f'    <td class="td_header" colSpan="3">{text}</td>')
        f.write("  </tr>")
        docstring = self.get_docstring(f"state_{state}")
        if docstring:
            f.write('<tr class="tr_comment">')
            f.write('  <td class="td_space">&nbsp;&nbsp;&nbsp;</td>')
            f.write('  <td class="td_label">comment</td>')
            f.write(f'  <td class="td_text">{docstring}</td>')
            f.write("</tr>")
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

    def doc_state_recursive(self, list_state):
        f = io.StringIO()
        for state, list_state in list_state:
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
        docstring = inspect.getdoc(self)
        if docstring:
            f.write("<p>" + docstring + "</p><br>")
        listHierarchy = self.get_hierarchy()
        s = self.doc_state_recursive(listHierarchy)
        f.write(s)
        f.write("</body>\n")
        f.write("</html>\n")
        return f.getvalue()


html_header = """
<!DOCTYPE html PUBLIC '-//W3C//DTD XHTML 1.0 Transitional//EN' 'http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd'>
<?xml version='1.0' encoding='iso-8859-1' ?>
<html xmlns='http://www.w3.org/1999/xhtml'>
  <head>
    <title>Hierarchical State Machine</title> 
    <meta http-equiv='content-type' content='text/html;charset=iso-8859-1'>
    <meta content='HSM by Maerki Informatik' name='description'>
    <style type='text/css'>
    <!--
    /*  common styles  */
    table.table_state {width: 100%; border-left: 2px solid #000000; border-right: 2px solid #000000; border-top: 0px solid #000000; border-bottom: 0px solid #000000}
    td.td_header { background-color: #EEEEEE; border-bottom: 1px solid #000000; border-top: 1px solid #000000; font-weight: bold}
    td.td_label {width: 1%; font-size: smaller; font-style: italic}
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
    hsm.BadStatemachineException: No corresponding state_TopA_SubB() for entry_TopA_SubB()!
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
    hsm.BadStatemachineException: No corresponding state_TopA_SubB() for exit_TopA_SubB()!
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
    'a': will be handled by TopA_SubA
        calling state "state_TopA_SubA(a)"
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
    'a': will be handled by TopA
        calling state "state_TopA(a)"
      a: was handled by state_TopA
    >>> sm.dispatch('b')
    'b': will be handled by TopA_SubA
        calling state "state_TopA_SubA(b)"
      b: was handled by state_TopA_SubA
        Calling entry_TopA_SubB
    >>> sm.dispatch('b')
    'b': will be handled by TopA_SubB
        calling state "state_TopA_SubB(b)"
        Empty Transition!
    >>> sm.dispatch('a')
    'a': will be handled by TopA_SubB
        calling state "state_TopA_SubB(a)"
      a: was handled by state_TopA
        Calling exit_TopA_SubB
    """

    def state_TopA(self, signal):
        if signal == "a":
            raise StateChangeException(self.state_TopA_SubA)
        raise IgnoreEventException()

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
    'r': will be handled by TopA
        calling state "state_TopA(r)"
      r: was handled by state_TopA
        Calling exit_TopA
        Calling entry_TopC
    >>> sm.dispatch('s')
    's': will be handled by TopC
        calling state "state_TopC(s)"
      s: was handled by state_TopC
        Calling exit_TopC
        Calling entry_TopB
        Calling entry_TopB_SubA
        Calling entry_TopB_SubA_SubsubA
    >>> sm.dispatch('t')
    't': will be handled by TopB_SubA_SubsubA
        calling state "state_TopB_SubA_SubsubA(t)"
      t: was handled by state_TopB_SubA_SubsubA
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


def test():
    import doctest

    return doctest.testmod()


if __name__ == "__main__":
    test()
