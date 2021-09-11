# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: InstrumentDriver_Interface.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 15288 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import ascii, bytes, chr, dict, filter, hex, input, int, map, next, oct, open, pow, range, round, str, super, zip
import time
dictPrefs = None

def setPreferences(dPrefs):
    """Set prefs dict object in the module, to make it available in drivers"""
    global dictPrefs
    dictPrefs = dPrefs


def getPreferences():
    """Get dict with preferences"""
    return dictPrefs


class Interface(object):
    __doc__ = 'Helper object for interfacing data between the GUI and the driver'
    OPEN = 0
    SET = 1
    GET = 2
    SET_CFG = 3
    GET_CFG = 4
    CLOSE = 5
    FORCE_CLOSE = 6
    ABORT_OPERATION = 7
    WAIT_FOR_SWEEP = 8
    REPEAT_SET = 9
    ARM = 10
    ERROR = 11
    INACTIVE = 12
    STATUS = 13
    PROGRESS = 14
    CURRENT = 15
    LOG = 16
    TERMINATED = 17
    OP_STATUS = (STATUS, PROGRESS, CURRENT, LOG)
    VALUE_FROM_USER = 18
    OP_INTERNAL = (VALUE_FROM_USER,)
    OP_NAMES = ('Open', 'Set value', 'Get value', 'Set config', 'Get config', 'Close',
                'Force close', 'Abort operation', 'Wait for sweep', 'Repeat set value',
                'Arm instrument', 'Error', 'Inactive', 'Status', 'Progress', 'Current value',
                'Log', 'Terminated', 'Value from user')

    def __init__(self, queueIn, queueOut, from_driver=False):
        """Helper object for interfacing data between the GUI and the driver"""
        super(Interface, self).__init__()
        self.queueIn = queueIn
        self.queueOut = queueOut
        self.bStopped = False
        self.from_driver = from_driver
        if not self.from_driver:
            self.iRef = 0
            self.dCallback = dict()

    def addOperationOpenInstr(self, callId=None, delay=None):
        """ Open instrument communication """
        dOp = dict()
        dOp['operation'] = Interface.OPEN
        self.addOperation(dOp, callId, delay)

    def addOperationSetValue(self, quant, value, rate=0.0, wait_for_sweep=True, callId=None, options={}, delay=None, callback=None):
        """ Set instrument value """
        sQuant = quant.name
        dOp = options.copy()
        dOp['operation'] = Interface.SET
        dOp['quant'] = sQuant
        if quant.isVector():
            dOp['value'] = quant.getTraceDict(value, bCopy=False)
        else:
            dOp['value'] = value
        dOp['sweep_rate'] = rate
        dOp['wait_for_sweep'] = wait_for_sweep
        self.addOperation(dOp, callId, delay, callback=callback)

    def addOperationGetValue(self, quant, callId=None, options={}, delay=None, callback=None):
        """ Get instrument value """
        sQuant = quant.name
        dOp = options.copy()
        dOp['operation'] = Interface.GET
        dOp['quant'] = sQuant
        self.addOperation(dOp, callId, delay, callback=callback)

    def addOperationArm(self, lQuantNames, callId=None, options={}, delay=None):
        """ Arm instrument for future call """
        dOp = options.copy()
        dOp['operation'] = Interface.ARM
        dOp['lQuant'] = lQuantNames
        self.addOperation(dOp, callId, delay)

    def addOperationSetCfg(self, lQuantNames, lValues, lRate, always_update_all, callId=None, delay=None):
        """Set instrument config, by setting a list of quantities"""
        dOp = dict()
        dOp['operation'] = Interface.SET_CFG
        dOp['lQuant'] = lQuantNames
        dOp['lValue'] = lValues
        dOp['lRate'] = lRate
        dOp['always_update_all'] = always_update_all
        self.addOperation(dOp, callId, delay)

    def addOperationGetCfg(self, lQuantNames, lOldValues, callId=None, delay=None):
        """Get instrument config, by getting a list of quantities"""
        dOp = dict()
        dOp['operation'] = Interface.GET_CFG
        dOp['lQuant'] = lQuantNames
        dOp['lValue'] = lOldValues
        self.addOperation(dOp, callId, delay)

    def addOperationAbort(self, quant=None, callId=None):
        """Abort current operations"""
        dOp = dict()
        dOp['operation'] = Interface.ABORT_OPERATION
        if quant is None:
            sQuant = None
        else:
            sQuant = quant.name
        dOp['quant'] = sQuant
        self.addOperation(dOp, callId)

    def addOperationWaitForSweep(self, quant, value=None, callId=None, options={}, delay=None):
        """ Set instrument value """
        sQuant = quant.name
        dOp = options.copy()
        dOp['operation'] = Interface.WAIT_FOR_SWEEP
        dOp['quant'] = sQuant
        dOp['value'] = value
        self.addOperation(dOp, callId, delay=delay)

    def addOperationCloseInstr(self, bForceQuit=False, callId=None, delay=None):
        """ Open instrument communication """
        dOp = dict()
        if bForceQuit:
            dOp['operation'] = Interface.FORCE_CLOSE
            self.setInterfaceStopped()
        else:
            dOp['operation'] = Interface.CLOSE
        self.addOperation(dOp, callId, delay)

    def addOperation(self, dOp, callId, delay=None, callback=None):
        """Add a dict defining an operation to the queue"""
        if self.from_driver or dOp['operation'] in Interface.OP_INTERNAL:
            dOp['call_id'] = callId
        else:
            self.iRef += 1
            self.dCallback[self.iRef] = (callId, callback)
            dOp['call_id'] = self.iRef
        dOp['delay'] = time.monotonic()
        if delay is not None:
            dOp['delay'] += delay
        self.queueIn.put(dOp)

    def updateResponseFromDriver(self, dOp):
        """Read response from driver"""
        if dOp.get('at_init', False):
            return dOp
        iRef = dOp.pop('call_id', None)
        if dOp['operation'] in Interface.OP_STATUS:
            callId, callback = self.dCallback.get(iRef, (None, None))
            dOp['call_id'] = callId
        else:
            callId, callback = self.dCallback.pop(iRef, (None, None))
            dOp['call_id'] = callId
            dOp['callback'] = callback
        return dOp

    def popOpenCalls(self):
        """Remove and return a list of all open call references"""
        lRef = list(self.dCallback.keys())
        lRef.sort()
        lCallId = [self.dCallback[iRef][0] for iRef in lRef]
        lCallId = [cid for cid in lCallId if cid is not None]
        self.dCallback = dict()
        return lCallId

    def sendDialogValue(self, value):
        """Report request for value from user dialog"""
        dOp = dict()
        dOp['operation'] = Interface.VALUE_FROM_USER
        dOp['value'] = value
        self.addOperation(dOp, callId=None)

    def reportOperation(self, dOp, callId=None):
        """Report operation to caller"""
        dOp['call_id'] = callId
        self.queueOut.put(dOp)

    def requestValueFromUser(self, value, text, title):
        """Report request for value from user dialog"""
        dOp = dict()
        dOp['operation'] = Interface.VALUE_FROM_USER
        dOp['value'] = value
        dOp['text'] = text
        dOp['title'] = title
        self.reportOperation(dOp)

    def reportError(self, error, callId=None, at_init=False):
        """ Open instrument communication """
        dOp = dict()
        dOp['operation'] = Interface.ERROR
        dOp['error'] = error
        if at_init:
            dOp['at_init'] = True
        self.reportOperation(dOp, callId)

    def reportOpen(self, dInstrOpt, callId=None):
        """ Open instrument communication """
        dOp = dict()
        dOp['operation'] = Interface.OPEN
        dOp['instr_options'] = dInstrOpt
        self.reportOperation(dOp, callId)

    def reportSet(self, quant, value, sweep_rate=None, callId=None, dt=None):
        """Report set value"""
        dOp = dict()
        dOp['operation'] = Interface.SET
        dOp['quant'] = quant.name
        dOp['value'] = value
        dOp['sweep_rate'] = sweep_rate
        if dt is not None:
            dOp['dt'] = dt
        self.reportOperation(dOp, callId)

    def reportGet(self, quant, value, callId=None, dt=None):
        """Report instrument value """
        dOp = dict()
        dOp['operation'] = Interface.GET
        dOp['quant'] = quant.name
        dOp['value'] = value
        if dt is not None:
            dOp['dt'] = dt
        self.reportOperation(dOp, callId)

    def reportWaitForSweep(self, quant, value, callId=None, dt=None):
        """Report instrument value """
        dOp = dict()
        dOp['operation'] = Interface.WAIT_FOR_SWEEP
        dOp['quant'] = quant.name
        dOp['value'] = value
        if dt is not None:
            dOp['dt'] = dt
        self.reportOperation(dOp, callId)

    def reportInactive(self, closed=False):
        """Report inactivity"""
        dOp = dict()
        dOp['operation'] = Interface.INACTIVE
        dOp['closed'] = closed
        self.reportOperation(dOp)

    def reportArm(self, callId=None):
        """Report inactivity"""
        dOp = dict()
        dOp['operation'] = Interface.ARM
        self.reportOperation(dOp, callId)

    def reportSetCfg(self, lQuantNames, lValues, lRate, callId=None):
        """Report SET instrument config, by setting a list of quantities"""
        dOp = dict()
        dOp['operation'] = Interface.SET_CFG
        dOp['lQuant'] = lQuantNames
        dOp['lValue'] = lValues
        dOp['lRate'] = lRate
        self.reportOperation(dOp, callId)

    def reportGetCfg(self, lQuantNames, lValues, callId=None):
        """REPORT GET instrument config, by getting a list of quantities"""
        dOp = dict()
        dOp['operation'] = Interface.GET_CFG
        dOp['lQuant'] = lQuantNames
        dOp['lValue'] = lValues
        self.reportOperation(dOp, callId)

    def reportAbort(self, callId=None):
        """Report abort current operations"""
        dOp = dict()
        dOp['operation'] = Interface.ABORT_OPERATION
        self.reportOperation(dOp, callId)

    def reportClose(self, callId=None):
        """Report close operation"""
        dOp = dict()
        dOp['operation'] = Interface.CLOSE
        self.reportOperation(dOp, callId)

    def reportLog(self, message, level=20):
        """Report log message"""
        dOp = dict()
        dOp['operation'] = Interface.LOG
        dOp['message'] = message
        dOp['level'] = level
        self.reportOperation(dOp)

    def reportStatus(self, message, callId=None):
        """Report status"""
        dOp = dict()
        dOp['operation'] = Interface.STATUS
        dOp['message'] = message
        self.reportOperation(dOp, callId)

    def reportProgress(self, progress, callId=None):
        """Report progress"""
        dOp = dict()
        dOp['operation'] = Interface.PROGRESS
        dOp['progress'] = progress
        self.reportOperation(dOp, callId)

    def reportCurrentValue(self, quant_name, value, callId=None):
        """Report status"""
        dOp = dict()
        dOp['operation'] = Interface.CURRENT
        dOp['quant'] = quant_name
        dOp['value'] = value
        self.reportOperation(dOp, callId)

    def reportTerminated(self):
        """Report status"""
        dOp = dict()
        dOp['operation'] = Interface.TERMINATED
        self.reportOperation(dOp)

    def isInterfaceStopped(self):
        """Return True if process stopped running or will stop shortly"""
        return self.bStopped

    def setInterfaceStopped(self):
        """Set variable for defining that process has been stopped"""
        self.bStopped = True