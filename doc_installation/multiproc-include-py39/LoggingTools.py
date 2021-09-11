# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: LoggingTools.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 5940 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import ascii, bytes, chr, dict, filter, hex, input, int, map, next, oct, open, pow, range, round, str, super, zip
import os, logging
import logging.handlers as RFHandler
queueLog = None

def setLogQueue(q):
    """Set log queue object in the module, to make it available globally"""
    global queueLog
    queueLog = q


def getLogQueue():
    """Get global log queue"""
    return queueLog


def getLogHandler(queue=None):
    if queue is None:
        queue = queueLog
    return QueueHandler(queue)


def prepareLoggingForDriver(queue, level=None):
    """Get logger for use in Labber driver, will use a QueueHandler"""
    logger = logging.getLogger('LabberDriver')
    if level is not None:
        logger.setLevel(level)
    if len(logger.handlers) == 0:
        h = getLogHandler(queue)
        logger.addHandler(h)
    return logger


def listener_configurer(sLogDir):
    if not os.path.exists(sLogDir):
        os.makedirs(sLogDir)
    sNetworkLog = os.path.join(sLogDir, 'network_log.txt')
    sInstrLog = os.path.join(sLogDir, 'instrument_log.txt')
    sNotifyLog = os.path.join(sLogDir, 'notification_log.txt')
    logNetwork = logging.getLogger('LabberNetworkFile')
    fh = RFHandler(sNetworkLog, maxBytes=2000000.0, backupCount=1, delay=True, encoding='utf-8')
    frmt = logging.Formatter('%(asctime)s:  %(message)s', '%Y-%m-%d %H:%M:%S')
    fh.setFormatter(frmt)
    logNetwork.addHandler(fh)
    fh.close()
    logInstr = logging.getLogger('LabberInstrumentFile')
    fh = RFHandler(sInstrLog, maxBytes=2000000.0, backupCount=1, delay=True, encoding='utf-8')
    frmt = logging.Formatter('%(asctime)s,%(msecs)03d:  %(message)s', '%H:%M:%S')
    fh.setFormatter(frmt)
    logInstr.addHandler(fh)
    fh.close()
    logNotify = logging.getLogger('LabberNotifyFile')
    fh = RFHandler(sNotifyLog, maxBytes=2000000.0, backupCount=1, delay=True, encoding='utf-8')
    frmt = logging.Formatter('%(asctime)s,%(msecs)03d:  %(message)s', '%Y-%m-%d %H:%M:%S')
    fh.setFormatter(frmt)
    logNotify.addHandler(fh)
    fh.close()


def listener_process(queue, sLogDir):
    listener_configurer(sLogDir)
    dLog = {'LabberNetwork':logging.getLogger('LabberNetworkFile'),  'LabberInstrument':logging.getLogger('LabberInstrumentFile'), 
     'LabberNotify':logging.getLogger('LabberNotifyFile'), 
     'LabberDriver':logging.getLogger('LabberInstrumentFile')}
    while 1:
        try:
            record = queue.get()
            if record is None:
                break
            else:
                logger = dLog[record.name]
                logger.handle(record)
        except Exception:
            import sys, traceback
            traceback.print_exc(file=(sys.stderr))


class QueueHandler(logging.Handler):
    __doc__ = '\n    This handler sends events to a queue. Typically, it would be used together\n    with a multiprocessing Queue to centralise logging to file in one process\n    (in a multi-process application), so as to avoid file write contention\n    between processes.\n\n    This code is new in Python 3.2, but this class can be copy pasted into\n    user code for use with earlier Python versions.\n    '

    def __init__(self, queue):
        """
        Initialise an instance, using the passed queue.
        """
        logging.Handler.__init__(self)
        self.queue = queue

    def enqueue(self, record):
        """
        Enqueue a record.

        The base implementation uses put_nowait. You may want to override
        this method if you want to use blocking, timeouts or custom queue
        implementations.
        """
        self.queue.put_nowait(record)

    def prepare(self, record):
        """
        Prepares a record for queueing. The object returned by this
        method is enqueued.
        
        The base implementation formats the record to merge the message
        and arguments, and removes unpickleable items from the record
        in-place.
        
        You might want to override this method if you want to convert
        the record to a dict or JSON string, or send a modified copy
        of the record while leaving the original intact.
        """
        self.format(record)
        record.msg = record.message
        record.args = None
        record.exc_info = None
        return record

    def emit(self, record):
        """
        Emit a record.

        Writes the LogRecord to the queue, preparing it first.
        """
        try:
            self.enqueue(self.prepare(record))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)