# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: SG_Preferences.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 36272 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import ascii, bytes, chr, dict, filter, hex, input, map, next, oct, open, pow, range, round, str, super, zip
from future import standard_library
standard_library.install_aliases()
import configparser, os, sys, functools, numpy as np, SG_String, threading, json, time
from SG_String import NumpyBinaryJSONEncoder, json_numpy_obj_hook
PY3 = sys.version_info > (3, )
__sBaseDir__ = os.path.dirname(os.path.abspath(__file__))

class INIFileError(Exception):
    __doc__ = ' Error raised if an INI file can not be parsed correctly '

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return str(self.value)

    def getLabel(self):
        return 'Error reading .ini configuration file'


def getValueFromINI(iniCfg, sSection, sKey, defaultValue):
    """ Returns an entry from the iniCfg"""
    lOption = iniCfg.options(sSection)
    if isinstance(defaultValue, list):
        if len(defaultValue) == 0 or isinstance(defaultValue[0], str):
            dt = str
        elif isinstance(defaultValue[0], (float, int)):
            dt = float
        elif isinstance(defaultValue[0], bool):
            dt = bool
        else:
            dt = str
        values = []
        for n1 in range(1000):
            sKeyN = '%s_%d' % (sKey, n1 + 1)
            if sKeyN in lOption:
                value = iniCfg.get(sSection, sKeyN)
                values.append(dt(value))
            else:
                break

        return values
    if sKey not in lOption:
        return defaultValue
    sValue = str(iniCfg.get(sSection, sKey).strip())
    if isinstance(defaultValue, bool):
        if sValue.lower() in ('1', 'true', 'on'):
            return True
        return False
    else:
        if isinstance(defaultValue, (float, int)):
            return float(sValue)
        if isinstance(defaultValue, (str, str)):
            return sValue


class Preferences(object):
    __doc__ = 'Represents a Preferences object'

    def __str__(self):
        if self.sCfgIni is not None:
            sHead = 'File: %s' % self.sCfgIni
        else:
            sHead = ''
        sRest = ''
        for cfgItem in self.lItem:
            sRest += '\n' + str(cfgItem)

        return sHead + sRest

    def __init__(self, sCfgIni=None, name='', lDictItem=None):
        """Init the prefs from a .ini config file or a list of items"""
        super(Preferences, self).__init__()
        self.sCfgIni = sCfgIni
        self.lDictItem = lDictItem
        self.lItem = []
        self.dItem = dict()
        self.json_file = None
        if sCfgIni is not None:
            self.getConfigItemsFromINI(sCfgIni)
        else:
            self.name = name
            self.version = ''
            self.addItemsToConfig(lDictItem)
        self.lock_operation = threading.Lock()

    def create_copy(self):
        """Create copy of preferences object"""
        cfg2 = Preferences(self.sCfgIni, self.name, self.lDictItem)
        for item in self.lItem:
            cfg2.setValue(item.name, self.getValue(item.name))

        cfg2.json_file = self.json_file
        return cfg2

    def loadCfgFromINI(self, sFile):
        """Load an .ini file and parse Preferences settings"""
        if PY3:
            iniCfg = configparser.ConfigParser(interpolation=None)
        else:
            iniCfg = configparser.RawConfigParser()
        sFile = os.path.splitext(sFile)[0] + '.ini'
        with open(sFile, 'r') as fp:
            iniCfg.readfp(fp)
        name = iniCfg.get('General settings', 'name')
        version = iniCfg.getfloat('General settings', 'version')
        if name != self.name:
            raise INIFileError('The file %s contains settings for %s instead of %s.', (
             sFile, name, self.name))
        for itemName, value in iniCfg.items('Values'):
            if itemName in self.dItem:
                item = self.dItem[itemName]
                if item.datatype == PrefsItem.DOUBLE:
                    value = float(value)
                elif item.datatype == PrefsItem.BOOLEAN:
                    value = iniCfg.getboolean('Values', itemName)
                elif item.datatype == PrefsItem.STRING_LIST:
                    sList = value.strip()
                    if sList == '':
                        value = []
                    elif sList.startswith('[') and sList.endswith(']'):
                        lEval = eval(sList)
                        value = []
                        for elem in lEval:
                            value.append(str(elem))

                    else:
                        value = [
                         sList]
                else:
                    value = str(value)
                item.setValue(value)

    def saveCfgToINI(self, sFile):
        """Save current Preferences to an INI file"""
        sFile = os.path.splitext(sFile)[0] + '.ini'
        if PY3:
            iniCfg = configparser.ConfigParser(interpolation=None)
        else:
            iniCfg = configparser.RawConfigParser()
        iniCfg.add_section('General settings')
        iniCfg.set('General settings', 'name', self.name)
        iniCfg.set('General settings', 'version', self.version)
        iniCfg.add_section('Values')
        for item in self.lItem:
            iniCfg.set('Values', item.name, item.getValue())

        with open(sFile, 'w') as fp:
            iniCfg.write(fp)

    def loadCfgFromJSON(self, file_path):
        """Load a JSON file and parse Preferences settings"""
        file_path = os.path.splitext(file_path)[0] + '.json'
        max_try = 5
        while 1:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    string_config = f.read()
                break
            except Exception:
                max_try -= 1
                if max_try <= 0:
                    raise
                time.sleep(0.2)

        config = json.loads(string_config, object_hook=json_numpy_obj_hook)
        self.setCfgFromDict(config)
        self.json_file = file_path

    def saveCfgToJSON(self, file_path=None):
        """Save current Preferences to a JSON file"""
        if file_path is None:
            if self.json_file is not None:
                file_path = self.json_file
            else:
                raise Exception('No output file specified.')
        file_path = os.path.splitext(file_path)[0] + '.json'
        config = self.getCfgAsDict()
        string_config = json.dumps(config, cls=NumpyBinaryJSONEncoder)
        max_try = 5
        while 1:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(string_config)
                break
            except Exception:
                max_try -= 1
                if max_try <= 0:
                    raise
                time.sleep(0.2)

        self.json_file = file_path

    def getCfgAsDict(self):
        """Return config as dict"""
        dCfg = {}
        for item in self.lItem:
            dCfg[item.name] = item.getValue()

        return dCfg

    def setCfgFromDict(self, dCfg):
        """Set config from dict"""
        for key, value in dCfg.items():
            self.setValue(key, value)

    def getValue(self, name):
        """Get a prefs value, using a mutex to be treadsafe"""
        with self.lock_operation:
            key = name.lower()
            if key in self.dItem:
                item = self.dItem[key]
                return item.getValue()
            return

    def setValue(self, name, value):
        """set a prefs value, using a mutex to be treadsafe"""
        with self.lock_operation:
            key = name.lower()
            if key in self.dItem:
                item = self.dItem[key]
                return item.setValue(value)

    def getItemNames(self):
        """ Return a list of strings with all items, in insertion order"""
        lName = []
        for item in self.lItem:
            lName.append(item.name)

        return lName

    def getItemsInsertOrder(self):
        lAll = self.lItem[:]
        return lAll

    def getActiveItems(self):
        """ Return a list with all items that are active in the
        current instrument state. The items are returned in insertion
        order.
        """
        keys = self.getItemNames()
        lActive = []
        for n, key in enumerate(keys):
            item = self.getItem(key)
            if item.isActive(lActive):
                lActive.append(item)

        return lActive

    def getItemsBySection(self):
        """Return (lSection, dItem[section]) with active section and items
        """
        lSection = self.getControlSections(self.lItem)
        dItemSection = {x:[] for x in lSection}
        for item in self.lItem:
            dItemSection[item.section].append(item)

        return (
         lSection, dItemSection)

    def getItem(self, name):
        """ Return the item defined by name """
        return self.dItem[name.lower()]

    def getControlGroups(self, lItem):
        """Find and return a list of strings with all groups in the items"""
        lGroup = []
        for item in lItem:
            if item.group not in lGroup:
                lGroup.append(item.group)

        return lGroup

    def getControlSections(self, lItem=None):
        """Find and return a list of strings with all sections in the items"""
        if lItem is None:
            lItem = self.lItem
        lSection = []
        for item in lItem:
            if item.section not in lSection:
                lSection.append(item.section)

        return lSection

    def getConfigItemsFromINI(self, sFile):
        """Reads an INI file from disk and returns a dict with the config"""
        if PY3:
            iniCfg = configparser.ConfigParser(interpolation=None)
        else:
            iniCfg = configparser.RawConfigParser()
        iniCfg.read(sFile)
        lSection = iniCfg.sections()
        dConfig = dict()
        sGenSection = 'General settings'
        dConfig['name'] = str(iniCfg.get(sGenSection, 'name'))
        dConfig['version'] = str(iniCfg.get(sGenSection, 'version'))
        lSection.remove(sGenSection)
        self.name = dConfig['name']
        self.version = dConfig['version']
        lDictItem = []
        for section in lSection:
            lOption = iniCfg.options(section)
            tempItem = PrefsItem()
            dCfgItem = tempItem.getConfigAsDict()
            for option in lOption:
                if option not in dCfgItem:
                    if option[:9] != 'combo_def':
                        if option[:11] != 'state_value':
                            if option[:9] != 'def_value':
                                raise INIFileError('Unknown option: The option "%s" in section "%s" is not recognized.' % (
                                 option, section))

            for key in list(dCfgItem.keys()):
                if key in lOption:
                    dCfgItem[key] = str(iniCfg.get(section, key).strip())

            if 'state_item' in lOption:
                dCfgItem['state_item'] = getValueFromINI(iniCfg, section, 'state_item', '')
                dCfgItem['state_values'] = getValueFromINI(iniCfg, section, 'state_value', [])
            else:
                dCfgItem['name'] = section
                sDatatype = iniCfg.get(section, 'datatype').strip().upper()
                if sDatatype == 'DOUBLE':
                    dCfgItem['datatype'] = PrefsItem.DOUBLE
                    dCfgItem['def_value'] = float(dCfgItem['def_value'])
                    dCfgItem['low_lim'] = float(dCfgItem['low_lim'])
                    dCfgItem['high_lim'] = float(dCfgItem['high_lim'])
                elif sDatatype == 'INT':
                    dCfgItem['datatype'] = PrefsItem.INT
                    dCfgItem['def_value'] = int(float(dCfgItem['def_value']))
                    try:
                        dCfgItem['low_lim'] = int(float(dCfgItem['low_lim']))
                    except:
                        dCfgItem['low_lim'] = int(-sys.maxsize / 2)

                    try:
                        dCfgItem['high_lim'] = int(float(dCfgItem['high_lim']))
                    except:
                        dCfgItem['high_lim'] = int(sys.maxsize / 2)

                elif sDatatype == 'BOOLEAN':
                    dCfgItem['datatype'] = PrefsItem.BOOLEAN
                    dCfgItem['def_value'] = bool(dCfgItem['def_value'])
                    dCfgItem['low_lim'] = 0.0
                    dCfgItem['high_lim'] = 1.0
                elif sDatatype == 'COMBO':
                    dCfgItem['datatype'] = PrefsItem.COMBO
                    dCfgItem['combo_defs'] = getValueFromINI(iniCfg, section, 'combo_def', [])
                    if 'def_value' not in lOption:
                        dCfgItem['def_value'] = dCfgItem['combo_defs'][0]
                    dCfgItem['low_lim'] = 0.0
                    dCfgItem['high_lim'] = len(dCfgItem['combo_defs']) - 1
                elif sDatatype == 'STRING':
                    dCfgItem['datatype'] = PrefsItem.STRING
                    if 'def_value' not in lOption:
                        dCfgItem['def_value'] = ''
                elif sDatatype == 'PATH':
                    dCfgItem['datatype'] = PrefsItem.PATH
                    if 'def_value' not in lOption:
                        dCfgItem['def_value'] = ''
                elif sDatatype == 'FOLDER':
                    dCfgItem['datatype'] = PrefsItem.FOLDER
                    if 'def_value' not in lOption:
                        dCfgItem['def_value'] = ''
                elif sDatatype == 'STRING_LIST':
                    dCfgItem['datatype'] = PrefsItem.STRING_LIST
                    dCfgItem['def_value'] = getValueFromINI(iniCfg, section, 'def_value', [])
                    if 'def_value' in lOption:
                        dCfgItem['def_value'] = []
                elif sDatatype == 'COLOR':
                    dCfgItem['datatype'] = PrefsItem.COLOR
                    if 'def_value' not in lOption:
                        dCfgItem['def_value'] = 'r'
                elif sDatatype == 'FONT':
                    dCfgItem['datatype'] = PrefsItem.FONT
                    if 'def_value' not in lOption:
                        dCfgItem['def_value'] = 'Arial,14'
                else:
                    raise INIFileError('Item in section "%s" in configuration "%s" has unknown datatype %s.' % (
                     section, dConfig['name'], sDatatype))
                lDictItem.append(dCfgItem)

        self.addItemsToConfig(lDictItem)

    def addItemsToConfig(self, lDictItem):
        """Add list with dict items to config"""
        dDictItem = dict()
        lDuplicate = []
        for dCfgItem in lDictItem:
            if dCfgItem['name'] not in dDictItem:
                dDictItem[dCfgItem['name']] = dCfgItem
            else:
                lDuplicate.append(dCfgItem)
            if dDictItem[dCfgItem['name']] not in lDuplicate:
                lDuplicate.append(dDictItem[dCfgItem['name']])

        for dCfgItem in lDuplicate:
            if dCfgItem['group'] is None:
                raise INIFileError('Item with name "%s" is not unique' % dCfgItem['name'])
            else:
                oldName = dCfgItem['name']
                newName = '%s: %s' % (dCfgItem['group'], dCfgItem['name'])
                dCfgItem['name'] = newName
                dCfgItem['label'] = oldName
                for dItem in lDictItem:
                    if dItem['group'] is not None:
                        if dItem['group'] == dCfgItem['group']:
                            if 'state_item' in dItem:
                                if dItem['state_item'] is not None:
                                    if dItem['state_item'] == oldName:
                                        dItem['state_item'] = newName

        if len(lDuplicate) > 0:
            dDictItem = dict()
            for dCfgItem in lDictItem:
                dDictItem[dCfgItem['name']] = dCfgItem

        for dCfgItem in lDictItem:
            if dCfgItem['state_item'] is not None:
                dtype = dDictItem[dCfgItem['state_item']]['datatype']
                lStateValue = []
                for sState in dCfgItem['state_values']:
                    if dtype == PrefsItem.BOOLEAN:
                        if isinstance(sState, bool):
                            lStateValue.append(sState)
                        elif sState.lower() in ('1', 'true', 'on'):
                            lStateValue.append(True)
                        else:
                            lStateValue.append(False)
                    else:
                        if dtype == PrefsItem.DOUBLE:
                            lStateValue.append(float(sState))
                        else:
                            lStateValue.append(sState)

                dCfgItem['state_values'] = lStateValue

        self.lItem = []
        self.dItem = {}
        for dCfgItem in lDictItem:
            cfgItem = PrefsItem(dCfgItem)
            self.lItem.append(cfgItem)
            self.dItem[dCfgItem['name'].lower()] = cfgItem


class PrefsItem(object):
    __doc__ = 'Represents a prefs item'
    DOUBLE = 'DOUBLE'
    INT = 'INT'
    BOOLEAN = 'BOOLEAN'
    COMBO = 'COMBO'
    STRING = 'STRING'
    PATH = 'PATH'
    FOLDER = 'FOLDER'
    STRING_LIST = 'STRING_LIST'
    COLOR = 'COLOR'
    FONT = 'FONT'
    DATATYPES = [
     DOUBLE, INT, BOOLEAN, COMBO, STRING, PATH, FOLDER, STRING_LIST, COLOR,
     FONT]
    _dCfgItem = {'name':'', 
     'group':None, 
     'section':'General', 
     'datatype':DOUBLE, 
     'def_value':0.0, 
     'unit':'', 
     'label':None, 
     'filter':'', 
     'low_lim':-np.inf, 
     'high_lim':np.inf, 
     'combo_defs':[],  'state_item':None, 
     'state_values':[],  'tooltip':''}

    def __str__(self):
        return '%s: %s' % (self.name, self.getValueString())

    def __init__(self, dCfgItem={}):
        """Init PrefsItem from dict"""
        self.name = ''
        self.group = None
        self.section = 'General'
        self.datatype = self.DOUBLE
        self.def_value = 0.0
        self.unit = ''
        self.label = None
        self.filter = ''
        self.low_lim = -np.inf
        self.high_lim = np.inf
        self.combo_defs = []
        self.state_item = None
        self.state_values = []
        self.tooltip = ''
        self.setConfigFromDict(dCfgItem)
        self._value = self.def_value
        self.ctrlGUI = None

    def getConfigAsDict(self):
        """Return the prefs item as a dict"""
        dCfgItem = dict()
        for key in PrefsItem._dCfgItem.keys():
            dCfgItem[key] = getattr(self, key)

        return dCfgItem

    def setConfigFromDict(self, dCfgItem):
        """Set the item prefs from a dict"""
        if 'datatype' in dCfgItem:
            dtype = dCfgItem['datatype']
            if dtype not in self.DATATYPES:
                name = dCfgItem.get('name', '')
                raise INIFileError('Item "%s" has unknown datatype "%s".' % (name, dtype))
        for key in list(PrefsItem._dCfgItem.keys()):
            if key in dCfgItem:
                setattr(self, key, dCfgItem[key])
            else:
                if key == 'def_value' and 'datatype' in dCfgItem:
                    if dCfgItem['datatype'] in (self.INT,):
                        self.def_value = int(0)
                    else:
                        if dCfgItem['datatype'] in (self.DOUBLE,):
                            self.def_value = 0.0
                        if dCfgItem['datatype'] in (self.BOOLEAN,):
                            self.def_value = False
                        if dCfgItem['datatype'] in (self.COMBO,):
                            self.def_value = dCfgItem['combo_defs'][0]
                        if dCfgItem['datatype'] in (self.STRING, self.PATH, self.FOLDER):
                            self.def_value = ''
                        if dCfgItem['datatype'] in (self.STRING_LIST,):
                            self.def_value = []
                        if dCfgItem['datatype'] in (self.COLOR,):
                            self.def_value = 'r'
                        if dCfgItem['datatype'] in (self.FONT,):
                            self.def_value = 'Arial,14'
                else:
                    setattr(self, key, PrefsItem._dCfgItem[key])

    def update_combo_names(self, names):
        """Update combobox item names, set to default if current not there"""
        if self.datatype != self.COMBO:
            return
        old_value = self.getValueString()
        self.combo_defs = names
        if self.ctrlGUI is not None:
            self.ctrlGUI.blockSignals(True)
            for n in range(self.ctrlGUI.count()):
                self.ctrlGUI.removeItem(0)

            self.ctrlGUI.addItems(names)
            self.ctrlGUI.blockSignals(False)
        if old_value in names:
            self.setValue(old_value)
        elif len(names) > 0:
            self.setValue(0)

    def getValue(self):
        """ Return current control value, taken from internal value """
        if isinstance(self._value, (list, tuple)):
            return self._value[:]
        return self._value

    def getValueIndex(self):
        """ Return current control value as a number, taken internally"""
        if self.datatype == self.BOOLEAN:
            return int(self._value)
        if self.datatype == self.COMBO:
            return self.combo_defs.index(self._value)
        return self._value

    def getValueString(self, value=None, unit=None):
        """ Return current control value as a string"""
        if value is None:
            value = self._value
        if unit is None:
            unit = self.unit
        if self.datatype == self.DOUBLE:
            if unit == '':
                return SG_String.getEngineeringString(value, iDigits=4)
            return SG_String.getSIPrefix(value, unit, iDecimals=4)[0]
        else:
            if self.datatype == self.INT:
                return str(value)
            if self.datatype == self.BOOLEAN:
                if value:
                    return 'On'
                return 'Off'
            if self.datatype == self.COMBO:
                if isinstance(value, (str, str)):
                    return str(value)
                return self.combo_defs[int(round(value))]
            else:
                if self.datatype in (self.STRING, self.PATH, self.FOLDER, self.COLOR):
                    return str(value)
                if self.datatype in (self.COLOR,):
                    return str(value)
                if self.datatype in self.FONT:
                    return str(value)
                if self.datatype in (self.STRING_LIST,):
                    return ', '.join(value)

    def getValueStringWithIndex(self, value=None):
        """ Return current control value as a string including the index"""
        if value is None:
            value = self._value
        sVal = self.getValueString(value)
        if self.datatype == self.BOOLEAN:
            if value:
                return '1: %s' % sVal
            return '0: %s' % sVal
        else:
            if self.datatype == self.COMBO:
                if isinstance(value, (str, str)):
                    value = self.combo_defs.index(value)
                return '%d: %s' % (value, sVal)
            return sVal

    def setValue(self, value):
        """Set control value, and update GUI control, if it exists. The function
        returns the same value, potentially typecast into the correct format"""
        if self.datatype == self.DOUBLE:
            self._value = float(value)
        elif self.datatype == self.INT:
            self._value = int(round(float(value)))
        elif self.datatype == self.BOOLEAN:
            if isinstance(value, (str, str)):
                setTrue = set(['1', 'true', 'on', 'yes'])
                if value.lower() in setTrue:
                    value = True
                else:
                    value = False
            self._value = bool(value)
        elif self.datatype == self.COMBO:
            if isinstance(value, (str, str)):
                if value in self.combo_defs:
                    self._value = value
            else:
                try:
                    self._value = self.combo_defs[int(value)]
                except Exception:
                    pass

        elif self.datatype in (self.STRING, self.PATH, self.FOLDER):
            self._value = str(value)
        elif self.datatype in (self.COLOR,):
            self._value = str(value)
        elif self.datatype in (self.FONT,):
            self._value = str(value)
        elif self.datatype in (self.STRING_LIST,):
            if isinstance(value, (list, tuple)):
                self._value = value
            else:
                self._value = [
                 value]
        if self.ctrlGUI is not None:
            if self.datatype in (self.DOUBLE, self.INT):
                self.ctrlGUI.setValue(self._value)
            elif self.datatype == self.BOOLEAN:
                self.ctrlGUI.setChecked(bool(self._value))
            elif self.datatype == self.COMBO:
                indx = self.ctrlGUI.findText(self._value)
                if indx >= 0:
                    self.ctrlGUI.setCurrentIndex(indx)
            elif self.datatype == self.STRING:
                self.ctrlGUI.setText(str(self._value))
            elif self.datatype in (self.PATH, self.FOLDER):
                self.ctrlGUI.setPath(str(self._value))
            elif self.datatype in (self.COLOR,):
                self.ctrlGUI.setColor(self._value)
            elif self.datatype in (self.FONT,):
                self.ctrlGUI.setFont(self._value)
            elif self.datatype in (self.STRING_LIST,):
                self.ctrlGUI.tableWidg.updateTable(self._value)
        if self.datatype == self.COMBO:
            if self._value in self.combo_defs:
                return self.combo_defs.index(self._value)
            return 0
        else:
            return self._value

    def isActive(self, lActive):
        """ Check if item is active, given the state of the items
        given in the lActive input list."""
        if self.state_item is None or (self.state_item == ''):
            return True
        for activeQ in lActive:
            if self.state_item == activeQ.name:
                state = activeQ.getValue()
                break
        else:
            return False
        if state in self.state_values:
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

    def removeControlReference(self):
        """Remove the GUI control reference, so it can be deleted"""
        self.ctrlGUI = None


if __name__ == '__main__':
    sFile = os.path.join(__sBaseDir__, 'LabberConfig.ini')
    cfg = Preferences(sFile)
    print(cfg)