# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: InstrumentConfig.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 78739 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import ascii, bytes, chr, dict, filter, hex, input, int, map, next, oct, open, pow, range, round, str, super, zip
import numpy as np, sys, copy, os, importlib, SG_String, SG_Object
try:
    import SG_HDF5
except Exception:
    pass

from ScriptsAndSettings import GENERIC_DRIVER, DataTypes, DataAccess
PY3 = sys.version_info > (3, )

def isInstrUniqueAndValid(lInstr, sHardware, comCfg, bCheckServer=False):
    """Method to check if a new instrument cfg is valid"""
    if comCfg.name == '':
        if comCfg.address == '' or (comCfg.interface == InstrumentComCfg.NONE):
            return False
        for instr in lInstr:
            if instr.isEqual(sHardware, comCfg, bCheckServer):
                return False

        return True


def make_controller_signal_str(driver_definition):
    """Change controller input/outputs to string, for use outside server"""
    if not driver_definition.get('controller', False):
        return driver_definition
    for d in driver_definition['quantities']:
        if d['name'] in ('Input signal', 'Output signal'):
            d['datatype'] = DataTypes.STRING

    return driver_definition


class Error(Exception):
    pass


class OptionError(Error):
    __doc__ = ' Exception if the instrument returns the wrong option string '

    def __init__(self, sOpt='', lAllowedOpt=[]):
        self.sOpt = sOpt
        self.lAllowedOpt = lAllowedOpt

    def __str__(self):
        sMsg = 'The instrument detected an unrecognized option string\n\nOption string reported: ' + str(self.sOpt) + '\n\nThe option string was expected to be one of the following:\n'
        sMsg += str(self.lAllowedOpt)
        return sMsg


class InstrumentQuantity(object):
    __doc__ = ' Represents a quantity that can be written to and/or read from\n    an instrument.\n    '
    DOUBLE = DataTypes.DOUBLE
    BOOLEAN = DataTypes.BOOLEAN
    COMBO = DataTypes.COMBO
    STRING = DataTypes.STRING
    VECTOR = DataTypes.VECTOR
    COMPLEX = DataTypes.COMPLEX
    VECTOR_COMPLEX = DataTypes.VECTOR_COMPLEX
    PATH = DataTypes.PATH
    BUTTON = DataTypes.BUTTON
    BOTH = DataAccess.BOTH
    READ = DataAccess.READ
    WRITE = DataAccess.WRITE
    NONE = DataAccess.NONE

    @staticmethod
    def getTraceDict(value=[], x0=0.0, dx=1.0, bCopy=False, x1=None, x=None, logX=False, t0=None, dt=None):
        """Format the value into a trace dict, with vector in numpy format"""
        if t0 is not None:
            x0 = t0
        if dt is not None:
            dx = dt
        if not isinstance(value, dict):
            if not isinstance(value, np.ndarray) or bCopy:
                value = np.array(value, ndmin=1)
            if x1 is not None:
                if logXand x0 > 0 and x0 > 0 and x is None:
                    x = np.logspace(np.log10(x0), np.log10(x1), len(value))
                else:
                    dx = (x1 - x0) / max(1.0, float(len(value) - 1))
                    logX = False
            value = {'y':value, 
             't0':x0,  'dt':dx}
            if x is not None:
                if not isinstance(x, np.ndarray) or bCopy:
                    x = np.array(x, ndmin=1)
                value['x'] = x
            return value
        if bCopy:
            dOut = value.copy()
            dOut['y'] = np.array((value['y']), ndmin=1)
            if 'x' in dOut:
                dOut['x'] = np.array((value['x']), ndmin=1)
            return dOut
        value['shape'] = value['y'].shape
        return value

    @staticmethod
    def getTraceXY(dTrace, bVsN=False):
        """Get (x,y)-traces (1D vectors) from trace dictionary"""
        vY = dTrace['y'].ravel()
        vX = dTrace.get('x', None)
        if bVsN:
            vX = 1 + np.arange((len(vY)), dtype=float)
        elif vX is not None:
            pass
        elif dTrace.get('logX', False):
            vX = 10 ** (dTrace['t0'] + np.arange((len(vY)),
              dtype=float) * dTrace['dt'])
        else:
            vX = dTrace['t0'] + np.arange((len(vY)), dtype=float) * dTrace['dt']
        return (vX, vY)

    def __init__(self, name='', unit='', datatype=DOUBLE, def_value=0.0, combo_defs=[], cmd_def=[], low_lim=-np.inf, high_lim=np.inf, group=None, enabled=True, state_quant=None, state_value=None, permission=BOTH, get_cmd='', set_cmd='', sweep_cmd=None, sweep_res=None, stop_cmd=None, sweep_check_cmd=None, x_name='Time', x_unit='s', model_value=[], option_value=[], section='', tooltip='', show_in_measurement_dlg=False, label=None, sweep_rate=0.0, sweep_minute=False, sweep_rate_low=0.0, sweep_rate_high=np.inf):
        self._value = def_value
        self.sweep_minute = sweep_minute
        scale = 60.0 if sweep_minute else 1.0
        self._sweeprate = sweep_rate / scale
        self.sweep_rate_low = sweep_rate_low / scale
        self.sweep_rate_high = sweep_rate_high / scale
        self.ctrlGUI = None
        self.name = name
        self.label = label
        self.unit = unit
        self.datatype = datatype
        self.def_value = def_value
        self.combo_defs = combo_defs
        self.cmd_def = cmd_def
        if self.datatype == self.DOUBLE:
            self.low_lim = low_lim
            self.high_lim = high_lim
            self._sweeprate = 0.0
        elif self.datatype == self.COMPLEX:
            self.low_lim = low_lim
            self.high_lim = high_lim
            self._sweeprate = 0.0
            self.def_value = self.setValue(self.def_value)
        elif self.datatype == self.BUTTON:
            self._value = True
            self.low_lim = 0.0
            self.high_lim = 1.0
        elif self.datatype == self.BOOLEAN:
            self.low_lim = 0.0
            self.high_lim = 1.0
        elif self.datatype == self.COMBO:
            self.low_lim = 0.0
            self.high_lim = len(self.combo_defs) - 1
        elif self.datatype in (self.STRING, self.PATH,
         self.VECTOR, self.VECTOR_COMPLEX):
            self.low_lim = 0.0
            self.high_lim = 0.0
        if self.datatype in (self.VECTOR, self.VECTOR_COMPLEX):
            self.x_name = x_name
            self.x_unit = x_unit
            self.setValue([])
        self.group = group
        if section == '':
            self.section = 'Settings'
        else:
            self.section = section
        self.enabled = enabled
        self.state_quant = state_quant
        if isinstance(state_value, list):
            self.state_value = state_value
        else:
            self.state_value = [
             state_value]
        self.model_value = model_value
        self.option_value = option_value
        self.permission = permission
        self.get_cmd = get_cmd
        self.set_cmd = set_cmd
        self.sweep_cmd = sweep_cmd
        self.sweep_res = sweep_res
        self.stop_cmd = stop_cmd
        self.sweep_check_cmd = sweep_check_cmd
        self.tooltip = tooltip
        self.show_in_measurement_dlg = show_in_measurement_dlg
        self.bValueUpdated = False
        self.sweep_target = None
        self.is_repeat_sweeping = False
        self._bValueChangedAtSet = False
        self.time_set = 0.0
        self.time_get = 0.0
        self.time_set_N = 0
        self.time_get_N = 0

    def resetTimeStatistics(self):
        """Reset timing statistics"""
        self.time_set = 0.0
        self.time_get = 0.0
        self.time_set_N = 0
        self.time_get_N = 0

    def updateTimeStatistics(self, dt, bSet=False):
        """Update counters for timing statistics for setting value"""
        if bSet:
            self.time_set += dt
            self.time_set_N += 1
            if self.time_set_N % 1000 == 0:
                avT, N = self.getTimeStatistics()
        else:
            self.time_get += dt
            self.time_get_N += 1

    def getTimeStatistics(self):
        """Return tuple (time per call, n of calls) with timing statistics"""
        if self.permission == self.READ:
            tot_time, n = self.time_get, self.time_get_N
        else:
            tot_time, n = self.time_set, self.time_set_N
        if n == 0:
            return (0.0, 0)
        return (
         tot_time / float(n), n)

    def getTimeStatisticsStr(self):
        """Return tuple (time per call, n of calls) with timing stats, as str"""
        tCall, nCall = self.getTimeStatistics()
        if nCall == 0:
            sNCall, sTCall = ('', '')
        else:
            sNCall = '%d' % nCall
            if tCall < 0.1:
                sTCall = '%.1f ms' % (1000 * tCall)
            elif tCall < 1.0:
                sTCall = '%.0f ms' % (1000 * tCall)
            else:
                sTCall = '%.2f s' % tCall
        return (
         sTCall, sNCall)

    def isSweepable(self):
        """Check if the quantitiy is sweepable"""
        bSweep = self.sweep_cmd is not None
        return bSweep

    def isVector(self):
        """Return true if quanity is a vector"""
        return self.datatype in (self.VECTOR, self.VECTOR_COMPLEX)

    def isComplex(self):
        """Return true if quanity value is represented by a complex number"""
        return self.datatype in (self.COMPLEX, self.VECTOR_COMPLEX)

    def getValue(self):
        """ Return current control value, taken from internal value """
        return self._value

    def getValueArray(self):
        """ Return current value as numpy array, taken from internal value"""
        if self.datatype in (self.VECTOR, self.VECTOR_COMPLEX):
            return self._value['y']
        return np.array([], dtype=float)

    def getSweepRate(self):
        """ Return current sweep rate, taken from internal value """
        return self._sweeprate

    def getValueIndex(self, value=None):
        """ Return current control value as a number, taken internally"""
        if value is None:
            value = self._value
        if self.datatype == self.BOOLEAN:
            return int(value)
        if self.datatype == self.COMBO:
            if isinstance(value, (str, str)):
                return self.combo_defs.index(value)
            return int(value)
        else:
            return value

    def getValueString(self, value=None, unit=None, digits=4):
        """ Return current control value as a string"""
        if value is None:
            value = self._value
        if unit is None:
            unit = self.unit
        if self.datatype == self.DOUBLE:
            if unit == '':
                return SG_String.getEngineeringString(value, iDigits=digits)
            return SG_String.getSIPrefix(value, unit, iDecimals=digits)[0]
        else:
            if self.datatype == self.COMPLEX:
                mag = abs(value)
                angle = np.angle(value, deg=True)
                string = SG_String.getEngineeringString(mag, iDigits=3)
                return '|%s|, %.1f%s' % (string, angle, chr(176))
            if self.datatype == self.BOOLEAN:
                if value:
                    return 'On'
                return 'Off'
            if self.datatype == self.COMBO:
                if isinstance(value, (str, str)):
                    return str(value)
                indx = int(round(value))
                if 0 <= indx < len(self.combo_defs):
                    return self.combo_defs[indx]
                return '<%d>' % indx
            else:
                if self.datatype in (self.STRING, self.PATH):
                    return str(value)
                if self.datatype == self.BUTTON:
                    return ''
                if self.isVector():
                    if isinstance(value, dict):
                        val = value['y'].ravel()
                    else:
                        val = value
                    if len(val) > 6:
                        n = 2
                        return str(val[:n])[:-1] + ', ..., ' + str(val[-n:])[1:]
                    return str(val)

    def getValueStringWithIndex(self, value=None):
        """ Return current control value as a string including the index"""
        if value is None:
            value = self._value
        sVal = self.getValueString(value)
        if self.datatype in (self.DOUBLE, self.STRING, self.PATH, self.VECTOR,
         self.COMPLEX, self.VECTOR_COMPLEX):
            return sVal
        if self.datatype == self.BOOLEAN:
            if value:
                return '1: %s' % sVal
            return '0: %s' % sVal
        else:
            if self.datatype == self.COMBO:
                if isinstance(value, (str, str)):
                    value = self.combo_defs.index(value)
                return '%d: %s' % (value, sVal)
            if self.datatype == self.BUTTON:
                return ''

    def setValue(self, value, rate=None):
        """Set control value, and update GUI control, if it exists. The function
        returns the same value, potentially typecast into the correct format"""
        oldValue = self._value
        self.bValueUpdated = True
        self._bValueChangedAtSet = False
        if self.datatype == self.DOUBLE:
            self._value = float(value)
            if rate is not None:
                self._sweeprate = float(rate)
        elif self.datatype == self.COMPLEX:
            self._value = complex(value)
        elif self.datatype == self.BOOLEAN:
            self._value = bool(value)
        elif self.datatype == self.COMBO:
            if isinstance(value, (int, float)) and int(value) < len(self.combo_defs):
                self._value = self.combo_defs[int(value)]
            elif isinstance(value, (str, str, float)):
                if value in self.combo_defs:
                    self._value = value
                else:
                    try:
                        lCmdFloat = [float(x) for x in self.cmd_def]
                        dValue = float(value)
                    except Exception:
                        lCmdFloat = []
                        dValue = 0.0

                    if dValue in lCmdFloat:
                        valueIndx = lCmdFloat.index(dValue)
                        self._value = self.combo_defs[valueIndx]
        elif self.datatype in (self.STRING, self.PATH):
            self._value = str(value)
        elif self.isVector():
            self._value = self.getTraceDict(value)
            self._bValueChangedAtSet = True
        if not self.isVector():
            if self._value != oldValue:
                self._bValueChangedAtSet = True
        if self.ctrlGUI is not None:
            try:
                self.ctrlGUI.setValueFromQuant(send_signal=(self._bValueChangedAtSet))
            except RuntimeError as e:
                try:
                    pass
                finally:
                    e = None
                    del e

            return self._value

    def isValueChangedAfterSet(self):
        """Return true if valid changed after last set value call"""
        return self._bValueChangedAtSet

    def isActive(self, lActive, instrCfg=None):
        """ Check if quantity is active, given the state of the quantities
        given in the lActive input list."""
        if instrCfg is not None:
            if len(self.model_value) > 0:
                if instrCfg.sModel not in self.model_value:
                    return False
            if len(self.option_value) > 0:
                bFound = False
                for sOpt in self.option_value:
                    if sOpt in instrCfg.lOption:
                        bFound = True

                if not bFound:
                    return False
                if self.state_quant is None or (self.state_quant == ''):
                    return True
                for activeQ in lActive:
                    if self.state_quant == activeQ.name:
                        state = activeQ.getValue()
                        break
                else:
                    return False
                if state in self.state_value:
                    return True
            return False

    def getLabelWithUnit(self, bUseFullName=True):
        """ Return a string with name and unit in the form: Voltage [V]"""
        if bUseFullName:
            name = self.name
        else:
            name = self.name if self.label is None else self.label
        if self.unit == '':
            return name
        return '%s [%s]' % (name, self.unit)

    def isPermissionReadWrite(self):
        """ Check the instrument read/write permission state of the quantity"""
        return self.permission == self.BOTH

    def isPermissionRead(self):
        """ Check the instrument read/write permission state of the quantity"""
        return self.permission == self.READ

    def isPermissionWrite(self):
        """ Check the instrument read/write permission state of the quantity"""
        return self.permission == self.WRITE

    def isPermissionNone(self):
        """ Check the instrument read/write permission state of the quantity"""
        return self.permission == self.NONE

    def isReadable(self):
        """Check if quantity can be read"""
        return self.isPermissionReadWrite() or self.isPermissionRead()

    def isWritable(self):
        """Check if quantity can be set"""
        return self.isPermissionReadWrite() or self.isPermissionWrite()

    def limits(self):
        """ returns a list with the limits"""
        return (
         self.low_lim, self.high_lim)

    def getDictWithCfg(self):
        """ returns the quantity config as a dict """
        value = [] if self.isVector() else self.getValue()
        return {'name':self.name, 
         'unit':self.unit, 
         'datatype':self.datatype, 
         'value':value, 
         'sweep_rate':self.getSweepRate(), 
         'combo_defs':self.combo_defs, 
         'low_lim':self.low_lim, 
         'high_lim':self.high_lim}

    def getCmdStringFromValue(self, value=None, dVisa={}):
        if value is None:
            value = self._value
        if self.datatype == self.DOUBLE:
            sConv = dVisa['str_value_out'] if 'str_value_out' in dVisa else '%.9e'
            sValue = sConv % value
        elif self.datatype == self.BOOLEAN:
            sOn = dVisa['str_true'] if 'str_true' in dVisa else '1'
            sOff = dVisa['str_false'] if 'str_false' in dVisa else '0'
            sValue = sOn if value else sOff
        elif self.datatype == self.COMBO:
            if isinstance(value, (str, str)):
                try:
                    valueIndx = self.combo_defs.index(value)
                    sValue = self.cmd_def[valueIndx]
                except (ValueError, IndexError):
                    raise OptionError(value, self.combo_defs)

            else:
                try:
                    sValue = self.cmd_def[int(value)]
                except (ValueError, IndexError):
                    raise OptionError(str(value), [str(n) for n in range(len(self.cmd_def))])

        else:
            sValue = str(value)
        return sValue

    def getValueFromCmdString(self, sValue, dVisa={}):
        """Inspect a string coming from an instrument and extract a value"""
        iStart = dVisa.get('str_value_strip_start', 0)
        iEnd = dVisa.get('str_value_strip_end', 0)
        if iStart > 0:
            sValue = sValue[int(iStart):]
        if iEnd > 0:
            sValue = sValue[:-int(iEnd)]
        if self.datatype == InstrumentQuantity.DOUBLE:
            try:
                value = float(sValue)
            except Exception:
                sValue = sValue.strip().upper()
                sOut = ''
                for c in sValue:
                    if c in '0123456789.+- E':
                        sOut += c
                    if len(sOut.strip()) > 0:
                        break

                while len(sOut) > 0:
                    if sOut[0] == 'E':
                        sOut = sOut[1:]

                while len(sOut) > 0:
                    if sOut[(-1)] == 'E':
                        sOut = sOut[:-1]

                if len(sOut) == 0:
                    raise
                value = float(sOut)

        elif self.datatype == InstrumentQuantity.BOOLEAN:
            setTrue = set(['1', 'true', 'on'])
            if 'str_true' in dVisa:
                setTrue.add(dVisa['str_true'].lower())
            if sValue.lower() in setTrue:
                value = True
            else:
                try:
                    value = float(sValue)
                    value = value > 0
                except Exception:
                    value = False

        elif self.datatype == InstrumentQuantity.COMBO:
            try:
                if sValue in self.cmd_def:
                    valueIndx = self.cmd_def.index(sValue)
                else:
                    try:
                        lCmdFloat = [float(x) for x in self.cmd_def]
                        dValue = float(sValue)
                    except Exception:
                        lCmdFloat = []
                        dValue = 0.0

                    valueIndx = lCmdFloat.index(dValue)
                value = self.combo_defs[valueIndx]
            except (ValueError, IndexError):
                raise OptionError(sValue, self.cmd_def)

        else:
            value = sValue
        return value


class InstrumentComCfg(object):
    __doc__ = 'Class for instruments communication configuration'
    GPIB = 'GPIB'
    TCPIP = 'TCPIP'
    USB = 'USB'
    PXI = 'PXI'
    ASRL = 'Serial'
    VISA = 'VISA'
    OTHER = 'Other'
    NONE = 'None'
    INTERFACE_OPTS = [GPIB, TCPIP, USB, PXI, ASRL, VISA, OTHER, NONE]
    SET_CONFIG = 'Set config'
    GET_CONFIG = 'Get config'
    DO_NOTHING = 'Do nothing'
    STARTUP_OPTS = [SET_CONFIG, GET_CONFIG, DO_NOTHING]
    _lServer = set(['localhost'])
    _sKeys = ('name', 'interface', 'address', 'startup', 'server', 'lock', 'show_advanced')
    _lAdvanced = [
     {'iniKey':'timeout', 
      'name':'Timeout', 
      'unit':'s',  'datatype':InstrumentQuantity.DOUBLE,  'def_value':10.0, 
      'low_lim':0.0,  'high_lim':np.inf,  'tooltip':'Maximum time to wait for instrument response'},
     {'iniKey':'term_char', 
      'name':'Term. character', 
      'unit':'',  'datatype':InstrumentQuantity.COMBO, 
      'def_value':'Auto',  'combo_defs':[
       'Auto', 'None', 'CR', 'LF', 'CR+LF'], 
      'tooltip':'Termination character used by the instrument'},
     {'iniKey':'send_end_on_write', 
      'name':'Send end on write', 
      'unit':'',  'datatype':InstrumentQuantity.BOOLEAN, 
      'def_value':True,  'tooltip':'Assert end during transfer of last byte of the buffer'},
     {'iniKey':'lock_visa', 
      'name':'Lock VISA resource', 
      'unit':'',  'datatype':InstrumentQuantity.BOOLEAN, 
      'def_value':False,  'tooltip':'Prevent other programs from accessing the VISA resource'},
     {'iniKey':'suppress_end_on_read', 
      'name':'Suppress end bit termination on read', 
      'unit':'',  'datatype':InstrumentQuantity.BOOLEAN, 
      'def_value':False, 
      'tooltip':'Suppress end bit termination on read',  'state_quant':'interface', 
      'state_value':TCPIP},
     {'iniKey':'tcpip_specify_port', 
      'name':'Use specific TCP port', 
      'unit':'',  'datatype':InstrumentQuantity.BOOLEAN, 
      'def_value':False, 
      'tooltip':'Use specific TCP port',  'state_quant':'interface', 
      'state_value':TCPIP},
     {'iniKey':'tcpip_port', 
      'name':'TCP port', 
      'unit':'',  'datatype':InstrumentQuantity.DOUBLE,  'def_value':0, 
      'low_lim':0,  'high_lim':65535,  'tooltip':'TCP port number', 
      'state_quant':'Use specific TCP port', 
      'state_value':True},
     {'iniKey':'tcpip_use_vicp', 
      'name':'Use VICP protocol', 
      'unit':'',  'datatype':InstrumentQuantity.BOOLEAN, 
      'def_value':False,  'tooltip':'Use VICP instead of TCPIP protocol, for Teledyne/Lecroy instruments', 
      'state_quant':'interface', 
      'state_value':TCPIP},
     {'iniKey':'baud_rate', 
      'name':'Baud rate', 
      'unit':'bps',  'datatype':InstrumentQuantity.DOUBLE, 
      'def_value':9600, 
      'low_lim':0.0,  'high_lim':np.inf,  'tooltip':'Communication speed for serial communication', 
      'state_quant':'interface', 
      'state_value':ASRL},
     {'iniKey':'data_bits', 
      'name':'Data bits', 
      'unit':'',  'datatype':InstrumentQuantity.DOUBLE, 
      'def_value':8, 
      'low_lim':1.0,  'high_lim':np.inf,  'tooltip':'Number of data bits for serial communication', 
      'state_quant':'interface', 
      'state_value':ASRL},
     {'iniKey':'stop_bits', 
      'name':'Stop bits', 
      'unit':'',  'datatype':InstrumentQuantity.DOUBLE,  'def_value':1.0, 
      'low_lim':1.0,  'high_lim':2.0,  'tooltip':'Number of stop bits for serial communication. Possible values are 1, 1.5 and 2', 
      'state_quant':'interface', 
      'state_value':ASRL},
     {'iniKey':'parity', 
      'name':'Parity', 
      'unit':'',  'datatype':InstrumentQuantity.COMBO,  'def_value':'No parity', 
      'combo_defs':[
       'No parity', 'Odd parity', 'Even parity'], 
      'tooltip':'Parity used for serial communication', 
      'state_quant':'interface', 
      'state_value':ASRL},
     {'iniKey':'gpib_board', 
      'name':'GPIB board number', 
      'unit':'',  'datatype':InstrumentQuantity.DOUBLE, 
      'def_value':0, 
      'low_lim':0,  'high_lim':np.inf,  'tooltip':'The GPIB board number starts from zero', 
      'state_quant':'interface', 
      'state_value':GPIB},
     {'iniKey':'gpib_go_to_local', 
      'name':'Send GPIB go to local at close', 
      'unit':'',  'datatype':InstrumentQuantity.BOOLEAN, 
      'def_value':False,  'tooltip':'Send GTL over GPIB after closing instrument', 
      'state_quant':'interface', 
      'state_value':GPIB},
     {'iniKey':'pxi_chassis', 
      'name':'PXI chassis', 
      'unit':'',  'datatype':InstrumentQuantity.DOUBLE, 
      'def_value':1, 
      'low_lim':0,  'high_lim':65535,  'tooltip':'PXI chassis number', 
      'state_quant':'interface', 
      'state_value':PXI},
     {'iniKey':'use_32bit_mode', 
      'name':'Run in 32-bit mode', 
      'unit':'',  'datatype':InstrumentQuantity.BOOLEAN, 
      'def_value':False,  'tooltip':'Run driver in 32-bit mode, for backwards compatibility'}]

    @staticmethod
    def getNamesAndDatatypesForHDf5():
        """Create lists of names, python datatype and hdf5 datatypes"""
        dt_interface = SG_HDF5.createEnumDatatype(InstrumentComCfg.INTERFACE_OPTS)
        dt_startup = SG_HDF5.createEnumDatatype(InstrumentComCfg.STARTUP_OPTS)
        dt_str = SG_HDF5.createStrDatatype()
        lKeys = [
         'name', 'interface', 'address', 'server', 'startup', 'lock',
         'show_advanced']
        lPythonDt = [str, str, str, str, str, bool, bool]
        lHdf5Dt = [
         dt_str, dt_interface, dt_str, dt_str, dt_startup, np.bool, np.bool]
        dToPython = {InstrumentQuantity.DOUBLE: float, 
         InstrumentQuantity.BOOLEAN: bool, 
         InstrumentQuantity.COMBO: str, 
         InstrumentQuantity.STRING: str}
        dToHdf5 = {InstrumentQuantity.DOUBLE: np.float, 
         InstrumentQuantity.BOOLEAN: np.bool, 
         InstrumentQuantity.COMBO: dt_str, 
         InstrumentQuantity.STRING: dt_str}
        for dQuant in InstrumentComCfg._lAdvanced:
            lKeys.append(dQuant['name'])
            lPythonDt.append(dToPython[dQuant['datatype']])
            lHdf5Dt.append(dToHdf5[dQuant['datatype']])

        return (
         lKeys, lPythonDt, lHdf5Dt)

    @staticmethod
    def updateServerList(lServer):
        """Update internal server list set for combo box option"""
        for sServer in lServer:
            InstrumentComCfg._lServer.add(sServer)

    @staticmethod
    def getDefaultConfigDict():
        """Define the default config"""
        dComCfg = dict()
        dComCfg['name'] = ''
        dComCfg['interface'] = InstrumentComCfg.GPIB
        dComCfg['address'] = ''
        dComCfg['startup'] = InstrumentComCfg.SET_CONFIG
        dComCfg['server'] = ''
        dComCfg['lock'] = False
        dComCfg['show_advanced'] = False
        for dQuant in InstrumentComCfg._lAdvanced:
            dComCfg[dQuant['name']] = dQuant['def_value']

        return dComCfg

    def __init__(self, dComCfg=None):
        """The initial settings is defined in the dComCfg dictionary"""
        dBaseCfg = InstrumentComCfg.getDefaultConfigDict()
        if dComCfg is not None:
            for key, val in dComCfg.items():
                if key in dBaseCfg:
                    dBaseCfg[key] = val

        self.name = dBaseCfg['name']
        self.interface = dBaseCfg['interface']
        self.address = dBaseCfg['address']
        self.startup = dBaseCfg['startup']
        self.server = dBaseCfg['server']
        self.lock = dBaseCfg['lock']
        self.show_advanced = dBaseCfg['show_advanced']
        self.bNoCom = False
        self.lAdvanced = []
        self.dAdvanced = dict()
        for dQuant in InstrumentComCfg._lAdvanced:
            dQuantCopy = dQuant.copy()
            if 'iniKey' in dQuantCopy:
                dQuantCopy.pop('iniKey')
            quant = InstrumentQuantity(**dQuantCopy)
            if dQuant['name'] in dBaseCfg:
                quant.setValue(dBaseCfg[dQuant['name']])
            self.lAdvanced.append(quant)
            self.dAdvanced[dQuant['name']] = quant
            if 'iniKey' in dQuant:
                self.dAdvanced[dQuant['iniKey']] = quant

    def setAdvancedValue(self, sQuant, value):
        """Set the value of a advanced setting"""
        if sQuant in self.dAdvanced:
            quant = self.dAdvanced[sQuant]
            quant.setValue(value)

    def getAddressString(self):
        """ Return a human-readable string describing the address"""
        address = self.address
        if self.interface == InstrumentComCfg.GPIB:
            return 'GPIB: %s' % address
        if self.interface == InstrumentComCfg.TCPIP:
            return 'IP: %s' % address
        if self.interface == InstrumentComCfg.USB:
            return 'USB: %s' % address
        if self.interface == InstrumentComCfg.PXI:
            if 'pxi_chassis' in self.dAdvanced:
                chassis = int(self.dAdvanced['pxi_chassis'].getValue())
            else:
                chassis = 1
            if chassis == 1:
                return 'PXI: %s' % address
            return 'PXI: %d:%s' % (chassis, address)
        else:
            if self.interface == InstrumentComCfg.ASRL:
                return 'Serial: %s' % address
            if self.interface == InstrumentComCfg.VISA:
                return 'VISA: %s' % address
            if self.interface == InstrumentComCfg.OTHER:
                return address
            if self.interface == InstrumentComCfg.NONE:
                return ''

    def getServer(self):
        """Return the server name, default to localhost if no name is given"""
        if self.server == '':
            return 'localhost'
        return self.server

    def isEqual(self, comCfg, bCheckServer=False):
        """Check if two ComConfigs are equal. Configs are considered equal if
        name or address are the same"""
        if bCheckServer:
            if self.getServer() != comCfg.getServer():
                return False
        nameOther = comCfg.name
        addressOther = comCfg.getAddressString()
        bNoneSelf = self.interface == InstrumentComCfg.NONE
        bNoneOther = comCfg.interface == InstrumentComCfg.NONE
        if bNoneSelf or (bNoneOther):
            return nameOther == self.name
        if self.name != '':
            if self.name == nameOther:
                return True
        return self.getAddressString() == addressOther

    def getComCfgDict(self):
        """Return a dict with the settings given by the GUI controls"""
        dComCfg = SG_Object.getConfigAsDict(self, InstrumentComCfg._sKeys)
        for quant in self.lAdvanced:
            dComCfg[quant.name] = quant.getValue()

        return dComCfg

    def setNoCommunication(self, bNoCom):
        """For instruments with no communication"""
        self.bNoCom = bNoCom
        if bNoCom:
            self.interface = InstrumentComCfg.NONE


class InstrumentCfg(object):
    __doc__ = 'Complete definition of an instrument, including a comCfg object'
    lIni = []

    @staticmethod
    def get_list_of_drivers(show_error_dlg=False, include_optimizer=False):
        """Reload driver definitions and store in class variable"""
        import DriverLibraryINI
        InstrumentCfg.lIni = DriverLibraryINI.getListOfDrivers(show_error_dlg=show_error_dlg,
          include_optimizer=include_optimizer)
        return InstrumentCfg.lIni

    @staticmethod
    def reload_driver(name):
        """Reload driver definition for given driver name"""
        for n, driver in enumerate(InstrumentCfg.lIni):
            if name.lower() == driver['name'].lower():
                break
        else:
            return
        import DriverLibraryINI
        driver_cfg = DriverLibraryINI.getInstrCfgFromINI(driver['config_path'])
        InstrumentCfg.lIni.pop(n)
        InstrumentCfg.lIni.insert(n, driver_cfg)
        return driver_cfg

    @staticmethod
    def createHDF5Entry_List(hdfRef, lInstrCfg):
        lKeys, lPyDt, lHdf5Dt = InstrumentComCfg.getNamesAndDatatypesForHDf5()
        dt_str = SG_HDF5.createStrDatatype()
        lKeys = ['hardware', 'version', 'id', 'model'] + lKeys
        lHdf5Dt = [dt_str, dt_str, dt_str, dt_str] + lHdf5Dt
        hdfGrp = hdfRef.create_group('Instrument config')
        lDict = []
        for n, instrCfg in enumerate(lInstrCfg):
            dComCfg = instrCfg.comCfg.getComCfgDict()
            dOption = instrCfg.getOptionsDict()
            dCfg = dComCfg.copy()
            instr_str = instrCfg.getIdString()
            dCfg['hardware'] = instrCfg.getHardwareName()
            dCfg['version'] = instrCfg.getVersion()
            dCfg['id'] = instr_str
            dCfg['model'] = dOption['model']
            lDict.append(dCfg)
            hdfInstr = hdfGrp.create_group(instr_str)
            SG_HDF5.setAttribute(hdfInstr, 'Installed options', dOption['options'])
            dValues = instrCfg.getValuesDict(bIncludeVector=False)
            for key, value in dValues.items():
                SG_HDF5.setAttribute(hdfInstr, key, value)

            lQuant = instrCfg.getActiveQuantities()
            for quant in lQuant:
                if quant.isVector():
                    dtype = complex if quant.isComplex() else float
                    SG_HDF5.setAttribute(hdfInstr, quant.name, np.array([], dtype=dtype))
                    if dCfg['hardware'] == GENERIC_DRIVER:
                        key = '___%s___x_name' % quant.name
                        SG_HDF5.setAttribute(hdfInstr, key, quant.x_name)
                        key = '___%s___x_unit' % quant.name
                        SG_HDF5.setAttribute(hdfInstr, key, quant.x_unit)
                else:
                    if dCfg['hardware'] == GENERIC_DRIVER:
                        if quant.datatype == quant.COMBO:
                            key = '___%s___combo_defs' % quant.name
                            SG_HDF5.setAttribute(hdfInstr, key, quant.combo_defs)

        SG_HDF5.createRecordFromDictList(hdfRef, 'Instruments', lDict, lKeys, lHdf5Dt)

    @staticmethod
    def updateHDF5InstrValues_List(hdfRef, lInstrCfg):
        """Static method for updating instrCfg values in a Hdf5 file"""
        hdfGrp = None
        for n, instrCfg in enumerate(lInstrCfg):
            if instrCfg.comCfg.startup != instrCfg.comCfg.GET_CONFIG:
                continue
            else:
                if hdfGrp is None:
                    hdfGrp = hdfRef['Instrument config']
                instr_str = instrCfg.getIdString()
                hdfInstr = hdfGrp[instr_str]
                dValues = instrCfg.getValuesDict(bIncludeVector=False)
                for key, value in dValues.items():
                    SG_HDF5.setAttribute(hdfInstr, key, value)

    @staticmethod
    def show_error_dlg_missing_driver(hardware, error):
        """Show error message dialog if failing to load driver def file"""
        try:
            from qtpy.QtWidgets import QMessageBox
            msgBox = QMessageBox()
            msgBox.setWindowTitle('Labber - Error')
            if hasattr(error, 'getLabel'):
                msgBox.setText(error.getLabel())
            else:
                msgBox.setText('An error occurred when creating a driver for the instrument "%s"' % hardware)
            msgBox.setInformativeText(str(error))
            msgBox.show()
            msgBox.raise_()
            msgBox.exec_()
        except Exception:
            raise error

    @staticmethod
    def create_instrument_list_from_dict(configs, reload_definitions=False, show_error_dlg=False, raise_error=False):
        """Create list of instruments from config in list of dict"""
        import DriverLibraryINI
        reloaded_defs = set()
        instruments = []
        for d in configs:
            if reload_definitions:
                if d['hardware'] not in reloaded_defs:
                    InstrumentCfg.reload_driver(d['hardware'])
                    reloaded_defs.add(d['hardware'])
            com_config = InstrumentComCfg(d['com_config'])
            try:
                instrument = InstrumentCfg(d['hardware'], com_config, d['version'])
                values, options = instrument.runScriptForUpgradingCfg(d['values'], d['options'])
                instrument.setOptionsDict(options)
                missing, updated = instrument.setValuesDict(values)
                instruments.append(instrument)
            except (Error, DriverLibraryINI.INIFileError, Exception) as e:
                try:
                    if raise_error:
                        raise
                    version = d.get('version', '1.0')
                    values = d.get('values', {})
                    options = d.get('options', {})
                    generic_dict = DriverLibraryINI.define_generic_driver(d['hardware'], version, values)
                    instrument = InstrumentCfg(comCfg=com_config,
                      dInstrCfg=generic_dict,
                      version=version)
                    instrument.setOptionsDict(options)
                    instrument.setValuesDict(values)
                    instruments.append(instrument)
                    if show_error_dlg:
                        InstrumentCfg.show_error_dlg_missing_driver(d['hardware'], e)
                finally:
                    e = None
                    del e

        return instruments

    @staticmethod
    def createInstrListFromHdf5(hdfRef, bShowError=False, bViewOnly=False, in_server=False, raise_error=False):
        import DriverLibraryINI
        lKeys, lPyDt, lHdf5Dt = InstrumentComCfg.getNamesAndDatatypesForHDf5()
        hdfGrp = hdfRef['Instrument config']
        lDict = SG_HDF5.readRecordToDictList(hdfRef['Instruments'])
        lInstrCfg = []
        controllers = []
        for dData in lDict:
            sHardware = dData['hardware']
            dComCfg = InstrumentComCfg.getDefaultConfigDict()
            for key, dt in zip(lKeys, lPyDt):
                if key in dData:
                    dComCfg[key] = dt(dData[key])

            version = str(dData['version'])
            instr_str = str(dData['id'])
            dOption = {'model':'', 
             'options':[]}
            if 'model' in dData:
                dOption['model'] = str(dData['model'])
            dValues = SG_HDF5.readAttributesToDict(hdfGrp[instr_str])
            if 'Installed options' in dValues:
                lOpt = dValues.pop('Installed options')
                for sOpt in lOpt:
                    dOption['options'].append(str(sOpt))

            comCfg = InstrumentComCfg(dComCfg)
            try:
                instrCfg = InstrumentCfg(sHardware, comCfg, version=version, in_server=in_server)
                dValues, dOption = instrCfg.runScriptForUpgradingCfg(dValues, dOption)
                instrCfg.setOptionsDict(dOption)
                lMissingQuant, updated_quants = instrCfg.setValuesDict(dValues)
                if bViewOnly:
                    if len(lMissingQuant) > 0:
                        raise Error()
                lInstrCfg.append(instrCfg)
                if instrCfg.isController():
                    controllers.append((instrCfg, dValues))
            except (Error, DriverLibraryINI.INIFileError, Exception) as e:
                try:
                    if raise_error:
                        raise
                    instrument_dict = DriverLibraryINI.define_generic_driver(sHardware, version, dValues)
                    instrCfg = InstrumentCfg(comCfg=comCfg,
                      dInstrCfg=instrument_dict,
                      version=version)
                    instrCfg.setOptionsDict(dOption)
                    instrCfg.setValuesDict(dValues)
                    lInstrCfg.append(instrCfg)
                    if bShowError:
                        InstrumentCfg.show_error_dlg_missing_driver(sHardware, e)
                finally:
                    e = None
                    del e

        for instrument_cfg, values in controllers:
            instrument_cfg.update_controller_signals(lInstrCfg)
            instrument_cfg.setValuesDict(values)

        return lInstrCfg

    def getIdString(self):
        """Return a unique ID string representing the instrument"""
        sHardware = self.getHardwareName()
        sAddress = self.comCfg.getAddressString()
        return '%s - %s, %s at %s' % (sHardware, sAddress, self.comCfg.name,
         self.comCfg.getServer())

    def getHardwareAndComCfgDict(self):
        """Return hardware name and ComCfg dict, for talking to server"""
        return (
         self.getHardwareName(), self.comCfg.getComCfgDict())

    def __init__(self, sHardware='', comCfg=InstrumentComCfg(), dInstrCfg=None, version=None, bClearIni=False, in_server=False):
        self.in_server = in_server
        if sHardware != '':
            import DriverLibraryINI
            if len(InstrumentCfg.lIni) == 0:
                InstrumentCfg.get_list_of_drivers(include_optimizer=True)
            elif bClearIni:
                InstrumentCfg.reload_driver(sHardware)
            dInstrCfg = DriverLibraryINI.getDriverDict(sHardware, InstrumentCfg.lIni)
            dInstrCfg = self._add_controller_quantities(dInstrCfg)
        self.dInstrCfg = dInstrCfg
        self.comCfg = comCfg
        self.comCfg.setNoCommunication(self.isSignalGenerator() or self.isSignalAnalyzer() or self.isController())
        self.dQuantity = dict()
        self.lKeys = []
        self.oldVersion = version
        if version is None or version == self.getVersion():
            self.fUpgradeDriverCfg = None
            self.dQuantReplace = dict()
        else:
            self.fUpgradeDriverCfg = self.getScriptForUpgradingCfg()
            self.runScriptForUpgradingCfg()
        if dInstrCfg['options'] is None or len(dInstrCfg['options']['model_str']) == 0:
            self.sModel = ''
        else:
            self.sModel = dInstrCfg['options']['model_str'][0]
        self.lOption = []
        self.instrCfgCtrl = None
        for quant in dInstrCfg['quantities']:
            self.addQuantity(quant)

    def get_instrument_config_as_dict(self, include_id=False):
        """Get instruments configuration as a python dictionary"""
        d = dict()
        d['hardware'] = self.getHardwareName()
        d['version'] = self.getVersion()
        if include_id:
            d['id'] = self.getIdString()
        d['options'] = self.getOptionsDict()
        d['com_config'] = self.comCfg.getComCfgDict()
        d['values'] = self.getValuesDict(bOnlyActive=True,
          bIncludeReadOnly=True,
          bIncludeVector=True,
          strip_vector_values=True)
        return d

    def getScriptForUpgradingCfg(self):
        """Look for a user-defined function for updating old versions of the
        driver"""
        dInstrCfg = self.dInstrCfg
        try:
            if dInstrCfg['driver_path'] is not None:
                sName = dInstrCfg['driver_path']
                sDir = os.path.split(dInstrCfg['config_path'])[0]
                if sDir not in sys.path:
                    sys.path.insert(0, sDir)
                sDir = os.path.join(sDir, sName)
                if sDir not in sys.path:
                    sys.path.insert(0, sDir)
                mod = importlib.import_module('%s-UpgradeCfg' % sName)
                return mod.upgradeDriverCfg
            return
        except Exception:
            return

    def runScriptForUpgradingCfg(self, dValue={}, dOption=[]):
        """Run user-defined script many times until we get latest version"""
        oldVersion = self.oldVersion
        newVersion = self.dInstrCfg['version']
        if self.fUpgradeDriverCfg is None or (oldVersion == newVersion):
            self.dQuantReplace = dict()
            return (
             dValue, dOption)
        version, dValue, dOption, dQuantReplace = self.fUpgradeDriverCfg(oldVersion, dValue, dOption)
        while version != oldVersion:
            if version != newVersion:
                oldVersion = version
                version, dValue, dOption, dQuantReplace2 = self.fUpgradeDriverCfg(oldVersion, dValue, dOption)
                for oldQuant, newQuant in list(dQuantReplace.items()):
                    for oldQuant2, newQuant2 in dQuantReplace2.items():
                        if oldQuant2 == newQuant:
                            dQuantReplace[oldQuant] = newQuant2

                for oldQuant2, newQuant2 in dQuantReplace2.items():
                    dQuantReplace[oldQuant2] = newQuant2

        self.dQuantReplace = dQuantReplace
        return (
         dValue, dOption)

    def addQuantity(self, cfg):
        """ Add a quantity to the instument driver.
        The cfg variable should be a dict defining at least the
        following keywords:
            name: (string)
            datatype: DOUBLE (possible types defined in InstrumentQuantity)
        and optionally defining these keywords:
            unit: (string)
            def_value: default value, type depending on datatype
            combo_defs: list of string containing combo box labels
            low_lim: lowest allowable value
            high_lim: highest allowable
            group: name of group containing similar quantities
            enabled: default enabled state
            state_quant: quantity setting availibility of this quantity
            state_value: list of state values for which this quantity is active
            permission: access to instrument, options are both/read/write/none
        """
        name = cfg['name']
        if name in self.dQuantity:
            raise Exception('Quantity %s is already defined.' % name)
        if 'state_quant' in cfg:
            if cfg['state_quant'] not in ('', None):
                if cfg['state_quant'] not in self.lKeys:
                    sError = 'State-defining quantity %s does not exist.' % cfg['state_quant']
                    raise Exception(sError)
                stQ = self.dQuantity[cfg['state_quant']]
                if stQ.datatype not in (stQ.COMBO, stQ.BOOLEAN):
                    sError = 'State-defining quantity %s is not a boolean or' + 'single-selection item list.' % cfg['state_quant']
                    raise Exception(sError)
        self.dQuantity[name] = InstrumentQuantity(**cfg)
        self.lKeys.append(name)

    def getQuantityNames(self):
        """ Return a list of strings with all quantities, in insertion order"""
        return self.lKeys

    def getQuantitiesInsertOrder(self):
        lAll = []
        for sName in self.getQuantityNames():
            lAll.append(self.dQuantity[sName])

        return lAll

    def getActiveQuantities(self, bOnlyDefaultShow=False):
        """Return a list with all quantities that are active in the
        current instrument state. The quantities are returned in insertion
        order."""
        keys = self.getQuantityNames()
        lActive = []
        lActiveShow = []
        for n, key in enumerate(keys):
            quant = self.getQuantity(key)
            if quant.isActive(lActive, instrCfg=self):
                lActive.append(quant)
                if quant.show_in_measurement_dlg:
                    lActiveShow.append(quant)

        if bOnlyDefaultShow:
            if len(lActiveShow) > 0:
                return lActiveShow
        return lActive

    def getVectorQuantities(self, bOnlyActive=True, bRead=True, bWrite=True):
        """ Return a list with all quantities that are active in the
        current instrument state and return vectors."""
        if bOnlyActive:
            lQuant = self.getActiveQuantities()
        else:
            lQuant = self.getQuantitiesInsertOrder()
        lVector = []
        for quant in lQuant:
            bReadQ = quant.isPermissionReadWrite() or quant.isPermissionRead()
            bWriteQ = quant.isPermissionReadWrite() or quant.isPermissionWrite()
            if quant.isVector():
                if not (bRead and bReadQ):
                    if bWrite:
                        if bWriteQ:
                            pass
                        lVector.append(quant)

        return lVector

    def getActiveQuantitiesString(self, bWithUnit=False):
        """ Return a list of strings with all quantities that are active in the
        current instrument state. The quantities are returned in insertion
        order."""
        lActive = self.getActiveQuantities()
        lString = []
        for n, quant in enumerate(lActive):
            if bWithUnit:
                lString.append(quant.getLabelWithUnit())
            else:
                lString.append(quant.name)

        return lString

    def getActiveQuantitiesByGroup(self):
        """Return (lGroup, dQuant[group]) with active groups and quantities"""
        lActive = self.getActiveQuantities()
        lGroups = self.getControlGroups(lActive)
        dQuant = {x:[] for x in lGroups}
        for quant in lActive:
            dQuant[quant.group].append(quant)

        return (
         lGroups, dQuant)

    def getQuantitiesInSetOrder(self, bReturnAll=False):
        """ Return a list with all quantites that are valid in the
        current instrument state. The quantities are sorted by permission
        group, in order:
            {none, write, read, both}.
        Within each subgroup, the quantities are returned in insertion order.
        """
        lNone = lWrite = lRead = lBoth = []
        if bReturnAll:
            lActive = self.getQuantitiesInsertOrder()
        else:
            lActive = self.getActiveQuantities()
        for n, quant in enumerate(lActive):
            if quant.isPermissionNone():
                lNone.append(quant)
            else:
                if quant.isPermissionWrite():
                    lWrite.append(quant)
                else:
                    if quant.isPermissionRead():
                        lRead.append(quant)
            if quant.isPermissionReadWrite():
                lBoth.append(quant)

        return lNone + lWrite + lRead + lBoth

    def getQuantity(self, name, bConvertOldVersion=False):
        """ Return the quantitiy defined by name """
        if bConvertOldVersion:
            if name in self.dQuantReplace:
                name = self.dQuantReplace[name]
        return self.dQuantity[name]

    def getValuesDict(self, bOnlyActive=True, bIncludeReadOnly=True, bIncludeVector=True, strip_vector_values=False):
        """ Return a dict with quantity name and values of all active quants in
        the current instrument state."""
        if bOnlyActive:
            lQuant = self.getActiveQuantities()
        else:
            lQuant = self.getQuantitiesInsertOrder()
        dValue = dict()
        for quant in lQuant:
            if not bIncludeReadOnly or quant.isPermissionRead():
                if not bIncludeVector or quant.isVector():
                    pass
                if quant.isVector():
                    if strip_vector_values:
                        dtype = complex if quant.isComplex() else float
                        dValue[quant.name] = np.array([], dtype=dtype)
                    else:
                        dValue[quant.name] = quant.getValue()
                else:
                    value = quant.getValue()
                    if quant.isComplex():
                        value = complex(value)
                    dValue[quant.name] = value
                if quant.isSweepable():
                    dValue['%s - Sweep rate' % quant.name] = quant.getSweepRate()

        return dValue

    def setValuesDict(self, dValue):
        """ Update the quantities with the values in the (name,value) dict"""
        not_available = []
        updated_quantities = []
        for name, value in dValue.items():
            if name in self.dQuantity:
                quant = self.dQuantity[name]
                if quant.isSweepable():
                    sweepName = '%s - Sweep rate' % quant.name
                    if sweepName in dValue:
                        sweepRate = dValue[sweepName]
                        quant.setValue(value, sweepRate)
                    else:
                        quant.setValue(value)
                else:
                    if quant.isPermissionRead():
                        continue
                    else:
                        quant.setValue(value)
                if quant.isValueChangedAfterSet():
                    updated_quantities.append(name)
            else:
                if not name.endswith(' - Sweep rate'):
                    not_available.append(name)

        return (
         not_available, updated_quantities)

    def getOptionsDict(self):
        """ Return a dict with current instrument option settings"""
        dOption = dict()
        dOption['model'] = self.sModel
        dOption['options'] = self.lOption[:]
        return dOption

    def setOptionsDict(self, dOption):
        """Set installed options and update control, if given"""
        if not self.dInstrCfg['options'] is None:
            if 'model' not in dOption or ('options' not in dOption):
                self.sModel = ''
                self.lOption = []
                return []
            lModel = self.dInstrCfg['options']['model_str']
            if dOption['model'] in lModel:
                self.sModel = dOption['model']
            elif len(lModel) > 0:
                self.sModel = lModel[0]
            else:
                self.sModel = ''
            lOption = dOption['options']
            lNoOption = []
            self.lOption = []
            for sOption in lOption:
                if sOption in self.dInstrCfg['options']['option_str']:
                    self.lOption.append(sOption)
                else:
                    lNoOption.append(sOption)

            if self.instrCfgCtrl is not None:
                self.instrCfgCtrl.updateCtrlFromOptions()
            return lNoOption

    def setModel(self, sModel):
        """Convenience function for setting instrument model string"""
        dOpt = self.getOptionsDict()
        dOpt['model'] = sModel
        self.setOptionsDict(dOpt)

    def setInstalledOptions(self, lOption):
        """Convenience function for setting instrument installed options"""
        dOpt = self.getOptionsDict()
        dOpt['options'] = lOption
        self.setOptionsDict(dOpt)

    def getControlGroups(self, lQuantity):
        """Find and return a list of strings with all groups in the quants"""
        lGroup = []
        for quant in lQuantity:
            if quant.group not in lGroup:
                lGroup.append(quant.group)

        return lGroup

    def getItemsBySection(self, bOnlyActive=False):
        """Return (lSection, dItem[section]) with active section and items
        """
        if bOnlyActive:
            lQuant = self.getActiveQuantities()
        else:
            lQuant = self.getQuantitiesInsertOrder()
        lSection = self.getControlSections(lQuant)
        dItemSection = {x:[] for x in lSection}
        for item in lQuant:
            dItemSection[item.section].append(item)

        return (
         lSection, dItemSection)

    def getControlSections(self, lQuant=None):
        """Find and return a list of strings with all sections in the items"""
        if lQuant is None:
            lQuant = self.getQuantitiesInsertOrder()
        lSection = []
        for item in lQuant:
            if item.section not in lSection:
                lSection.append(item.section)

        return lSection

    def getVersion(self):
        """ Return a string with the name of the controlled hardware"""
        return self.dInstrCfg['version']

    def getHardwareName(self, bWithAddress=False, bWithName=False):
        """ Return a string with the name of the controlled hardware"""
        if bWithAddress:
            sHardware = self.dInstrCfg['name']
            sAddress = self.comCfg.getAddressString()
            sName = self.comCfg.name
            sOutput = sHardware
            if sAddress != '':
                sOutput += ' - %s' % sAddress
            if bWithName:
                if sName != '':
                    sOutput += ' - %s' % sName
            return sOutput
        if bWithName:
            sHardware = self.dInstrCfg['name']
            sName = self.comCfg.name
            if sName == '':
                sName = self.comCfg.getAddressString()
            return '%s - %s' % (sHardware, sName)
        return self.dInstrCfg['name']

    def getBaseName(self, bWithAddress=False):
        """ Return a string with the base name, for making channels unique"""
        if self.comCfg.name != '':
            sBase = self.comCfg.name
        else:
            sBase = self.getHardwareName(bWithAddress=bWithAddress)
        return sBase

    def getInstrCfgDict(self):
        return self.dInstrCfg

    def supportArm(self):
        """Check if instrument supports arming"""
        return self.dInstrCfg['support_arm']

    def supportHardwareLoop(self):
        """Check if instrument supports hardware loop mode"""
        return self.dInstrCfg['support_hardware_loop']

    def isSignalGenerator(self):
        """Return True if instrument is a signal generator"""
        return self.dInstrCfg['signal_generator']

    def isSignalAnalyzer(self):
        """Return True if instrument is a signal analyzer"""
        return self.dInstrCfg['signal_analyzer']

    def isController(self):
        """Return True if instrument is a controller"""
        return self.dInstrCfg.get('controller', False)

    def _add_controller_quantities(self, driver_definition):
        """Add controller quantities to the driver definition dictionary"""
        if not driver_definition.get('controller', False):
            return driver_definition
        driver_copy = copy.deepcopy(driver_definition)
        quantities = [
         dict(name='Controller enabled',
           label='Enabled',
           datatype=(DataTypes.BOOLEAN),
           def_value=True,
           group='Controller settings'),
         dict(name='Controller period',
           label='Period',
           unit='s',
           datatype=(DataTypes.DOUBLE),
           def_value=1.0,
           low_lim=0.0,
           group='Controller settings'),
         dict(name='Measured controller period',
           label='Measured period',
           datatype=(DataTypes.DOUBLE),
           def_value=1.0,
           unit='s',
           group='Controller settings'),
         dict(name='Input signal',
           label='',
           datatype=(DataTypes.COMBO),
           def_value='',
           combo_defs=[''],
           group='Signals'),
         dict(name='Input value',
           unit='',
           datatype=(DataTypes.DOUBLE),
           group='Signals'),
         dict(name='Output signal',
           label='',
           datatype=(DataTypes.COMBO),
           def_value='',
           combo_defs=[''],
           group='Signals'),
         dict(name='Output value',
           unit='',
           datatype=(DataTypes.DOUBLE),
           permission=(DataAccess.READ),
           group='Signals')]
        if not self.in_server:
            for d in quantities:
                if d['name'] in ('Input signal', 'Output signal'):
                    d['datatype'] = DataTypes.STRING

        for d in quantities:
            d['section'] = 'Controller'

        for d in quantities:
            driver_copy['quantities'].append(d)

        return driver_copy

    def update_controller_signals(self, instruments):
        """Update list of possible signals for controllers"""
        input_names = [
         '']
        output_names = ['']
        for instrument in instruments:
            if not instrument is self:
                if not instrument.isSignalAnalyzer():
                    if instrument.isSignalGenerator():
                        continue
                    else:
                        base_name = instrument.getHardwareName(bWithName=True) + ' - '
                        active_quantities = instrument.getActiveQuantities()
                        for quant in active_quantities:
                            if not quant.isPermissionWrite():
                                input_names.append(base_name + quant.name)
                            if not quant.isPermissionRead():
                                output_names.append(base_name + quant.name)

        for name in ('Input signal', 'Output signal'):
            quant = self.getQuantity(name)
            names = input_names if name.startswith('Input') else output_names
            old_value = quant.getValueString()
            if old_value not in names:
                old_value = ''
            else:
                quant.combo_defs = names
                if quant.ctrlGUI is not None:
                    quant.ctrlGUI._ctrl.blockSignals(True)
                    quant.ctrlGUI._ctrl.clear()
                    quant.ctrlGUI._ctrl.addItems(names)
                    quant.ctrlGUI._ctrl.blockSignals(False)
                quant.setValue(old_value)

    def isEqual(self, sHardware, comCfg, bCheckServer=False):
        """Compare the instr described by hardware and ComCfg and
        check if is equal to self. Configs are considered equal if hardware
        and ComCfg name or address are the same."""
        return sHardware == self.getHardwareName() and self.comCfg.isEqual(comCfg, bCheckServer)

    def getCopy(self, reload_definition=False):
        """Create a copy of the current instrCfg, removing any GUI references"""
        dOption = self.getOptionsDict()
        dValue = self.getValuesDict()
        if reload_definition:
            InstrumentCfg.reload_driver(self.getHardwareName())
        newInstr = InstrumentCfg((self.getHardwareName()),
          (self.comCfg), in_server=(self.in_server))
        newInstr.setOptionsDict(dOption)
        newInstr.setValuesDict(dValue)
        return newInstr


if __name__ == '__main__':
    pass