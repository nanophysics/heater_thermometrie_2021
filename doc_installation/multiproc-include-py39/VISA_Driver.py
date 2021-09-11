# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: VISA_Driver.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 19875 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import ascii, bytes, chr, dict, filter, hex, input, int, map, next, oct, open, pow, range, round, str, super, zip
import sys, os
from ScriptsAndSettings import MAC
import BaseDriver
from BaseDriver import LabberDriver
from InstrumentConfig import InstrumentComCfg, InstrumentQuantity
from InstrumentDriver_Interface import Interface, getPreferences
dPrefs = getPreferences()
CRLF = '\r\n'
try:
    if dPrefs is not None and dPrefs['VISA library'] != '':
        sPath = os.path.normpath(dPrefs['VISA library'])
        if not os.path.isfile(sPath):
            if MAC:
                sPath = os.path.join(sPath, 'VISA')
            else:
                sPath = os.path.join(sPath, 'visa32.dll')
        import visa
        rm = visa.ResourceManager(sPath)
    else:
        import visa
        rm = visa.ResourceManager()
except Exception as e:
    try:
        raise BaseDriver.VisaLibraryError('An error occurred when opening the VISA library.  Make sure the latest version of NI-VISA is installed.\n\n' + str(e))
    finally:
        e = None
        del e

class VISA_Driver(LabberDriver):
    __doc__ = ' This class implements get/set instrument value with VISA communication '

    def writeAndLog(self, sCmd='', bCheckError=True):
        """Convenience method for logging write commands sent to VISA"""
        self.log(('%s: VISA send: %s' % (self.sName, sCmd)), level=15)
        self.com.write(sCmd)
        if self.dVisa['always_read_after_write']:
            sReply = self.read()
            self.log(('%s: VISA receive after send: %s' % (self.sName, sReply)), level=15)
        if bCheckError:
            self.queryErrors()

    def askAndLog(self, sCmd='', bCheckError=True):
        """Convenience method for logging ask requests sent to VISA"""
        self.log(('%s: VISA send: %s' % (self.sName, sCmd)), level=15)
        sData = self.com.query(sCmd)
        if self.bAutoRemoveTerm:
            sData = sData.rstrip(CRLF)
        self.log(('%s: VISA receive: %s' % (self.sName, sData)), level=15)
        if bCheckError:
            self.queryErrors()
        return sData

    def write(self, sCmd='', bCheckError=True):
        """Convenience method for sending data to VISA"""
        self.com.write(sCmd)
        if self.dVisa['always_read_after_write']:
            sReply = self.read()
        if bCheckError:
            self.queryErrors()

    def write_raw(self, data):
        """Send raw data bytes to VISA resource"""
        self.com.write_raw(data)

    def read_raw(self, size=None):
        """Read raw data bytes from VISA resource"""
        return self.com.read_raw(size=size)

    def ask(self, sCmd='', bCheckError=True):
        """Convenience method for reading data from VISA"""
        sData = self.com.query(sCmd)
        if bCheckError:
            self.queryErrors()
        return sData

    def read(self, n_bytes=None, ignore_termination=False):
        """Read data from VISA.  If n_bytes is not specified, all data is read"""
        if n_bytes is None:
            if ignore_termination:
                sData = self.com.read_raw()
            else:
                sData = self.com.read()
                if self.bAutoRemoveTerm:
                    sData = sData.rstrip(CRLF)
        else:
            sData = self.com.read_bytes(n_bytes)
        return sData

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""
        dVisa = self.dInstrCfg['visa']
        self.dVisa = dVisa
        timeout = int(1000 * self.dComCfg['Timeout'])
        self.com = None
        try:
            if self.dComCfg['interface'] == InstrumentComCfg.GPIB:
                try:
                    sAddress = self.dComCfg['address']
                    lGPIB = sAddress.split(':')
                    if len(lGPIB) > 1:
                        nBoard, nGPIB = int(lGPIB[0]), int(lGPIB[1])
                    else:
                        nBoard, nGPIB = int(self.dComCfg['GPIB board number']), int(lGPIB[0])
                except ValueError as e:
                    try:
                        msg = 'Incorrect address string.'
                        raise BaseDriver.CommunicationError(msg)
                    finally:
                        e = None
                        del e

                sVISA = 'GPIB%d::%d' % (nBoard, nGPIB)
                self.log(sVISA, level=15)
                self.com = rm.open_resource(sVISA)
            elif self.dComCfg['interface'] == InstrumentComCfg.TCPIP:
                if self.dComCfg['Use specific TCP port']:
                    sVISA = 'TCPIP0::%s::%d::SOCKET' % (
                     self.dComCfg['address'], int(self.dComCfg['TCP port']))
                else:
                    sVISA = 'TCPIP0::%s::INSTR' % self.dComCfg['address']
                if self.dComCfg['Use VICP protocol']:
                    sVISA = 'VICP::%s::INSTR' % self.dComCfg['address']
                    from pyvisa.resources import MessageBasedResource
                    self.com = rm.open_resource(sVISA, resource_pyclass=MessageBasedResource)
                else:
                    self.com = rm.open_resource(sVISA)
                try:
                    from pyvisa.constants import VI_ATTR_TCPIP_KEEPALIVE, VI_TRUE
                    self.com.set_visa_attribute(VI_ATTR_TCPIP_KEEPALIVE, VI_TRUE)
                except:
                    pass

                try:
                    from pyvisa.constants import VI_ATTR_SUPPRESS_END_EN, VI_FALSE, VI_TRUE
                    dSupp = {False:VI_FALSE, 
                     True:VI_TRUE}
                    self.com.set_visa_attribute(VI_ATTR_SUPPRESS_END_EN, dSupp[self.dComCfg['Suppress end bit termination on read']])
                except:
                    pass

            elif self.dComCfg['interface'] == InstrumentComCfg.ASRL:
                try:
                    nSerial = int(self.dComCfg['address'])
                    sVISA = 'ASRL%d::INSTR' % nSerial
                except ValueError as e:
                    try:
                        sVISA = self.dComCfg['address']
                    finally:
                        e = None
                        del e

                from pyvisa.constants import Parity, StopBits
                dParity = {'No parity':Parity.none, 
                 'Odd parity':Parity.odd,  'Even parity':Parity.even}
                if self.dComCfg['Stop bits'] < 1.4:
                    stop_bits = StopBits.one
                elif self.dComCfg['Stop bits'] >= 1.6:
                    stop_bits = StopBits.two
                else:
                    stop_bits = StopBits.one_and_a_half
                self.com = rm.open_resource(sVISA, baud_rate=(int(self.dComCfg['Baud rate'])),
                  data_bits=(int(self.dComCfg['Data bits'])),
                  stop_bits=stop_bits,
                  parity=(dParity[self.dComCfg['Parity']]))
            elif self.dComCfg['interface'] == InstrumentComCfg.USB:
                sVISA = 'USB::%s::INSTR' % self.dComCfg['address']
                self.com = rm.open_resource(sVISA)
            elif self.dComCfg['interface'] == InstrumentComCfg.PXI:
                chassis = int(self.dComCfg.get('pxi_chassis', 1))
                slot = int(self.dComCfg['address'])
                sVISA = 'PXI::CHASSIS%d::SLOT%d' % (chassis, slot)
                self.com = rm.open_resource(sVISA)
            else:
                self.com = rm.open_resource(self.dComCfg['address'])
            sTerm = self.dComCfg['Term. character']
            dTerm = {'Auto':self.com.CR + self.com.LF,  'None':None,  'CR':self.com.CR,  'LF':self.com.LF, 
             'CR+LF':self.com.CR + self.com.LF}
            self.com.write_termination = dTerm.get(sTerm, None)
            self.bAutoRemoveTerm = sTerm == 'Auto'
            if self.bAutoRemoveTerm:
                self.com.read_termination = None
            else:
                self.com.read_termination = self.com.write_termination
            self.com.send_end = self.dComCfg['Send end on write']
            self.com.timeout = timeout
            if self.dComCfg.get('Lock VISA resource', False):
                self.com.lock_excl()
            if dVisa['reset']:
                self.com.clear()
                self.writeAndLog('*CLS;', bCheckError=False)
            self.checkModelAndOptions()
            if dVisa['query_instr_errors']:
                self.writeAndLog('*CLS;', bCheckError=False)
            if dVisa['init'] != '':
                self.writeAndLog(dVisa['init'])
        except visa.Error as e:
            try:
                msg = str(e)
                raise BaseDriver.CommunicationError(msg)
            finally:
                e = None
                del e

    def checkModelAndOptions(self):
        """Check model and options, update the internal instrCfg"""
        dOptionCfg = self.dInstrCfg['options']
        if dOptionCfg['check_model']:
            name = self.askAndLog((dOptionCfg['model_cmd']), bCheckError=False)
            for validId, validName in zip(dOptionCfg['model_id'], dOptionCfg['model_str']):
                if name.find(validId) >= 0:
                    break
            else:
                raise BaseDriver.IdError(name, dOptionCfg['model_id'])
            self.instrCfg.setModel(validName)
        if dOptionCfg['check_options']:
            lOption = []
            name = self.askAndLog((dOptionCfg['option_cmd']), bCheckError=False)
            for sOptId, sOptName in zip(dOptionCfg['option_id'], dOptionCfg['option_str']):
                if sOptId in name:
                    lOption.append(sOptName)

            self.instrCfg.setInstalledOptions(lOption)

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        dVisa = self.dInstrCfg['visa']
        try:
            if self.com is None:
                return
        except:
            return
        else:
            try:
                try:
                    if dVisa['final'] != '':
                        self.writeAndLog((dVisa['final']), bCheckError=False)
                    if self.dComCfg['interface'] == InstrumentComCfg.GPIB:
                        if self.dComCfg.get('Send GPIB go to local at close', False):
                            from pyvisa.constants import VI_GPIB_REN_ADDRESS_GTL
                            self.com.control_ren(VI_GPIB_REN_ADDRESS_GTL)
                    if self.dComCfg.get('Lock VISA resource', False):
                        self.com.unlock()
                except visa.Error as e:
                    try:
                        if not bError:
                            msg = str(e)
                            raise BaseDriver.CommunicationError(msg)
                    finally:
                        e = None
                        del e

            finally:
                try:
                    self.com.close()
                    del self.com
                except:
                    pass

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        try:
            sValue = quant.getCmdStringFromValue(value, self.dInstrCfg['visa'])
            if sweepRate != 0.0:
                if quant.datatype == InstrumentQuantity.DOUBLE:
                    currValue = quant.getValue()
                    sRate = '%.6e' % sweepRate
                    sCmd = quant.sweep_cmd
                    bOk = False
                    indx = sCmd.find('<sr>')
                    if indx >= 0:
                        sCmd = sCmd.replace('<sr>', sRate)
                        bOk = True
                    indx = sCmd.find('<st>')
                    if indx >= 0:
                        currValue = self.performGetValue(quant)
                        if value == currValue:
                            return currValue
                        dSweepTime = abs(value - currValue) / sweepRate
                        dSweepTime = max(dSweepTime, 0.1)
                        sSweepTime = '%.1f' % dSweepTime
                        sCmd = sCmd.replace('<st>', sSweepTime)
                        bOk = True
                    if not bOk:
                        raise BaseDriver.InstrStateError((Interface.SET), (self.sName),
                          sQuant=(quant.name), message='Sweep command not properly defined.  The command string has to inclued the string <sr> or <st>, which marks the position of sweep rate/sweep time.')
                    indx = sCmd.find('<*>')
                    if indx >= 0:
                        sMsg = sCmd.replace('<*>', sValue)
                    else:
                        sMsg = '%s %s' % (sCmd, sValue)
                    self.writeAndLog(sMsg, bCheckError=False)
                    return value
            sCmd = quant.set_cmd
            if sCmd == '':
                return value
            if quant.datatype == InstrumentQuantity.BUTTON:
                self.writeAndLog(sCmd)
                return value
            indx = sCmd.find('<*>')
            if indx >= 0:
                sMsg = sCmd.replace('<*>', sValue)
            else:
                sMsg = '%s %s' % (sCmd, sValue)
            self.writeAndLog(sMsg)
            return value
        except visa.Error as e:
            try:
                msg = str(e)
                raise BaseDriver.CommunicationError(msg)
            finally:
                e = None
                del e

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        try:
            sCmd = quant.get_cmd
            if sCmd == '':
                sCmd = '%s?' % quant.set_cmd
            if sCmd == '' or (sCmd == '?'):
                return quant.getValue()
            sAns = self.askAndLog(sCmd).strip()
            value = quant.getValueFromCmdString(sAns, self.dInstrCfg['visa'])
            return value
        except visa.Error as e:
            try:
                msg = str(e)
                raise BaseDriver.CommunicationError(msg)
            finally:
                e = None
                del e

    def checkIfSweeping(self, quant, options={}):
        """Check if instrument is sweeping the given quantity"""
        if quant.sweep_check_cmd is not None:
            if quant.sweep_check_cmd != '':
                sValue = self.askAndLog(quant.sweep_check_cmd)
                setTrue = set(['1', 'true', 'on'])
                dVisa = self.dInstrCfg['visa']
                if 'str_true' in dVisa:
                    setTrue.add(dVisa['str_true'].lower())
                if sValue.lower() in setTrue:
                    bSweeping = True
                else:
                    try:
                        bSweeping = float(sValue) > 0
                    except:
                        bSweeping = False

                return bSweeping
        return LabberDriver.checkIfSweeping(self, quant, options=options)

    def performStopSweep(self, quant, options={}):
        """Send command to instrument to stop sweep"""
        sStopCmd = quant.stop_cmd
        if sStopCmd is not None:
            self.writeAndLog(sStopCmd)

    def queryErrors(self):
        dVisa = self.dInstrCfg['visa']
        if dVisa['query_instr_errors']:
            status = int(self.askAndLog('*ESR?', bCheckError=False))
            status = status & int(dVisa['error_bit_mask'])
            if status > 0:
                if dVisa['error_cmd'] != '':
                    sMsg = self.askAndLog((dVisa['error_cmd']), bCheckError=False)
                else:
                    sMsg = ''
                self.writeAndLog('*CLS', bCheckError=False)
                raise BaseDriver.DeviceStatusError(status, sMsg)


if __name__ == '__main__':
    pass