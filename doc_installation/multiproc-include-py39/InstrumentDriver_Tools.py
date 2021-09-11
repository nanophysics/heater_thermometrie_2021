# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: InstrumentDriver_Tools.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 3126 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import ascii, bytes, chr, dict, filter, hex, input, int, map, next, oct, open, pow, range, round, str, super, zip
import sys, os, importlib, traceback
from BaseDriver import LabberDriver
import InstrumentDriver_Interface
from InstrumentDriver_Interface import Interface
from LoggingTools import prepareLoggingForDriver

def startDriverProcess(dInstrCfg=None, dComCfg=None, dValues=None, dOption=None, dPrefs={}, queue_in=None, queue_out=None, queue_log=None, log_level=20, callId=None):
    """Helper function for starting up the LabberDriver process"""
    InstrumentDriver_Interface.setPreferences(dPrefs)
    try:
        logger = prepareLoggingForDriver(queue_log, log_level)
        sApp = dPrefs.get('Application folder', '')
        sAPI = os.path.join(sApp, 'Script')
        if sAPI not in sys.path:
            sys.path.insert(0, sAPI)
        if dInstrCfg['driver_path'] is not None:
            sName = dInstrCfg['driver_path']
            sDir = os.path.split(dInstrCfg['config_path'])[0]
            if sDir not in sys.path:
                sys.path.insert(0, sDir)
            sDir = os.path.join(sDir, sName)
            if sDir not in sys.path:
                sys.path.insert(0, sDir)
            mod = importlib.import_module(sName)
            driver = mod.Driver(dInstrCfg, dComCfg, dValues, dOption, dPrefs, queue_in, queue_out, logger)
        elif dInstrCfg['visa'] is not None:
            from VISA_Driver import VISA_Driver
            driver = VISA_Driver(dInstrCfg, dComCfg, dValues, dOption, dPrefs, queue_in, queue_out, logger)
        else:
            driver = LabberDriver(dInstrCfg, dComCfg, dValues, dOption, dPrefs, queue_in, queue_out, logger)
    except Exception:
        sTraceBack = traceback.format_exc()
        interface = Interface(queue_in, queue_out, from_driver=True)
        interface.reportError(('An error occurred when starting the instrument.\n\n' + sTraceBack),
          callId, at_init=True)
        interface.reportInactive(closed=True)
        return
    else:
        driver.mainLoop()