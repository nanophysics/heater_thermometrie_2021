# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: ScriptsAndSettings.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 21484 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import ascii, bytes, chr, dict, filter, hex, input, int, map, next, oct, open, pow, range, round, str, super, zip
try:
    from multiprocessing import spawn
except Exception:
    pass

try:
    import msgpack
except Exception:
    pass

import sys, os, imp, datetime, warnings, functools, time

class Timer(object):
    __doc__ = 'Helper class for timing function calls'

    def __init__(self):
        self.t0 = time.perf_counter()

    def print_timestamp(self, message):
        t1 = time.perf_counter()
        dt = t1 - self.t0
        print('%s: %.1f ms' % (message, 1000 * dt))
        self.t0 = t1

    def get_timestamp(self):
        t1 = time.perf_counter()
        dt = t1 - self.t0
        self.t0 = t1
        return dt


def timer_decorator(func):
    """Print the runtime of the decorated function"""

    @functools.wraps(func)
    def wrapper_timer(*args, **kwargs):
        start_time = time.perf_counter()
        value = func(*args, **kwargs)
        end_time = time.perf_counter()
        run_time = end_time - start_time
        print('Finished %s in %.2f ms' % (
         func.__name__, 1000 * run_time))
        return value

    return wrapper_timer


MAC = sys.platform == 'darwin'
WIN = sys.platform.startswith('win')
LINUX = sys.platform.startswith('linux')
PY3 = sys.version_info > (3, )
if PY3:
    from time import perf_counter as timer
elif WIN:
    from time import clock as timer
else:
    from time import time as timer
version = '1.7.7'
version_logger = '1.1.3'
prefs_object = None
optimizer_process = None
optimizer_interface = None
logger_mode = False
STEP_NAME_API = 'Step index API'
OPTIMIZER_NAME = 'Labber Optimizer'
OPTIMIZER_STEP_ITEM = 'Iteration'
OPTIMIZER_CHANNEL = '%s - %s' % (OPTIMIZER_NAME, OPTIMIZER_STEP_ITEM)
GENERIC_DRIVER = 'Generic'
START_HIDDEN_MEASUREMENT_ENGINE = 'START_HIDDEN_MEASUREMENT_ENGINE'

def main_is_frozen():
    """Check if frozen"""
    return getattr(sys, 'frozen', False) or getattr(sys, 'importers', False) or imp.is_frozen('__main__')


def get_main_dir(bGetMainAppPath=False):
    if main_is_frozen():
        sPath = os.path.dirname(sys.executable)
        if not bGetMainAppPath:
            return sPath
        if MAC:
            sPath = '/Applications/Labber'
        elif os.path.split(sPath)[1] == 'Program':
            sPath = os.path.split(sPath)[0]
        return sPath
    return os.path.dirname(os.path.abspath(__file__))


sBaseDir = get_main_dir()
if main_is_frozen():
    warnings.filterwarnings('ignore')
if not main_is_frozen():
    sub = os.path.join(os.path.split(get_main_dir())[0], 'Subroutines')
    if sub not in sys.path:
        sys.path.append(sub)
import SG_Preferences, SG_String

def getVersionNumber(version_str=None):
    """Get version as number, 1.2.3 => 123"""
    global version
    if version_str is None:
        version_str = version
    if not isinstance(version_str, str):
        version_str = str(version_str)
    version_list = version_str.split('.')
    version_number = 0
    for n, value in enumerate([100, 10, 1]):
        if n < len(version_list):
            version_number += value * int(version_list[n][0])

    return version_number


def get_settings_path():
    """Return path to settings and temporary item files"""
    if MAC or LINUX:
        settings_path = os.path.join(os.path.expanduser('~'), '.config', 'Labber')
    else:
        settings_path = os.path.join(os.path.expanduser('~'), 'AppData', 'Roaming', 'Labber')
    return os.path.normpath(settings_path)


def get_preferences_file():
    """Return path to preferences file"""
    prefs_file = os.path.join(get_settings_path(), 'LabberPrefs.json')
    return os.path.normpath(prefs_file)


def create_preferences_object():
    """Create preferences object and make available in global variable"""
    global prefs_object
    sFile = os.path.join(get_main_dir(), 'Config', 'LabberConfig.ini')
    prefs_object = SG_Preferences.Preferences(sFile)
    return prefs_object


def getPreferences():
    """Return preferences object, will initiate if not already present"""
    global prefs_object
    if prefs_object is None:
        prefs_object = create_preferences_object()
        try:
            prefs_object.loadCfgFromJSON(get_preferences_file())
        except Exception:
            pass

        return prefs_object


def reload_preferences():
    """Reload preferences from disk"""
    preferences = getPreferences()
    try:
        prefs_object.loadCfgFromJSON(get_preferences_file())
    except Exception:
        pass

    return preferences


def init_preferences_and_folders():
    """Initiate preferences and default folders"""
    global logger_mode
    preferences = getPreferences()
    user_path = os.path.join(os.path.expanduser('~'), 'Labber')
    settings_path = get_settings_path()
    try:
        if not os.path.exists(settings_path):
            os.makedirs(settings_path, exist_ok=True)
    except Exception:
        pass

    preferences.setValue('Temporary items', settings_path)
    if not logger_mode or main_is_frozen():
        if not MAC or preferences.getValue('Application folder') == '':
            sAppPath = get_main_dir(bGetMainAppPath=True)
            preferences.setValue('Application folder', sAppPath)
        sAppPath = preferences.getValue('Application folder')
        driver_path = preferences.getValue('Instrument drivers')
        optimizer_path = preferences.getValue('Optimizer functions')
        if driver_path == '':
            preferences.setValue('Instrument drivers', os.path.join(sAppPath, 'Drivers'))
        if preferences.getValue('Local drivers') == '':
            sLocalPath = os.path.join(user_path, 'Drivers')
            preferences.setValue('Local drivers', sLocalPath)
            try:
                if not os.path.exists(user_path):
                    os.mkdir(user_path)
                if not os.path.exists(sLocalPath):
                    os.mkdir(sLocalPath)
            except Exception:
                pass

            if optimizer_path == '':
                preferences.setValue('Optimizer functions', os.path.join(sAppPath, 'Script', 'Optimizers'))
            if sAppPath.startswith('C:\\Program Files\\Labber'):
                if driver_path.startswith('C:\\Program Files (x86)\\Labber'):
                    preferences.setValue('Instrument drivers', os.path.join(sAppPath, 'Drivers'))
                if optimizer_path.startswith('C:\\Program Files (x86)\\Labber'):
                    preferences.setValue('Optimizer functions', os.path.join(sAppPath, 'Script', 'Optimizers'))
            if preferences.getValue('Local optimizers') == '':
                sLocalPath = os.path.join(user_path, 'Optimizers')
                preferences.setValue('Local optimizers', sLocalPath)
                try:
                    if not os.path.exists(user_path):
                        os.mkdir(user_path)
                    if not os.path.exists(sLocalPath):
                        os.mkdir(sLocalPath)
                except Exception:
                    pass

                if preferences.getValue('Database folder') == '':
                    sDataPath = os.path.join(user_path, 'Data')
                    preferences.setValue('Database folder', sDataPath)
                    try:
                        if not os.path.exists(user_path):
                            os.mkdir(user_path)
                        if not os.path.exists(sDataPath):
                            os.mkdir(sDataPath)
                    except Exception:
                        pass

            if preferences.getValue('Logger folder') == '':
                sLoggerPath = os.path.join(user_path, 'Logger Data')
                preferences.setValue('Logger folder', sLoggerPath)
                try:
                    if not os.path.exists(user_path):
                        os.mkdir(user_path)
                    if not os.path.exists(sLoggerPath):
                        os.mkdir(sLoggerPath)
                except Exception:
                    pass


def start_optimizer_process():
    """Start optimizer process"""
    global optimizer_interface
    global optimizer_process
    import multiprocessing, Optimizer_Interface
    queueTo = multiprocessing.Queue()
    queueFrom = multiprocessing.Queue()
    interface = Optimizer_Interface.InterfaceToOptimizer(queueTo, queueFrom)
    process = multiprocessing.Process(target=(Optimizer_Interface.startOptimizer),
      args=(
     queueTo, queueFrom))
    startProcess(process, use_default_distribution=False)
    optimizer_process = process
    optimizer_interface = interface


def save_scenario_from_dict(file_name, config):
    """Save scenario as binary .labber file"""
    base_name, ext = os.path.splitext(file_name)
    if ext.lower() == '.json':
        data = SG_String.dump_to_json_numpy_text(config)
        file_name_labber = file_name
    else:
        file_name_labber = base_name + '.labber'
        data = msgpack.packb(config,
          default=(SG_String.encodeMsgPack), use_bin_type=True)
    with open(file_name_labber, 'wb') as f:
        f.write(data)
    return file_name_labber


def load_scenario_as_dict(file_name):
    """Load scenario from binary .labber file"""
    base_name, ext = os.path.splitext(file_name)
    if ext.lower() == '.json':
        with open(file_name, 'rb') as f:
            data = f.read()
        config = SG_String.load_from_json_numpy_text(data)
    else:
        file_name_labber = base_name + '.labber'
        with open(file_name_labber, 'rb') as f:
            data = f.read()
        config = msgpack.unpackb(data,
          object_hook=(SG_String.decodeMsgPack), encoding='utf-8', use_list=True)
    return config


def createLogPath(sLogName, dateObj=None, bCreatePath=True, logger_mode=False, bConfigFile=False):
    """Return the path to a new log, creating folders if necessary"""
    preferences = getPreferences()
    if dateObj is None:
        dateObj = datetime.datetime.today()
    if logger_mode:
        sPathBase = preferences.getValue('Logger folder')
        if bConfigFile:
            return os.path.join(sPathBase, sLogName, sLogName + '.hdf5')
        sFolder = dateObj.strftime('%Y-%m')
        sPath = os.path.join(sPathBase, sLogName, sFolder)
        sLogName = sLogName + dateObj.strftime('-%Y%m%d')
    else:
        sYear = dateObj.strftime('%Y')
        sMonth = dateObj.strftime('%m')
        sDay = dateObj.strftime('Data_%m%d')
        sPathBase = preferences.getValue('Database folder')
        sPath = os.path.join(sPathBase, sYear, sMonth, sDay)
    if bCreatePath:
        try:
            os.makedirs(sPath)
        except OSError as exception:
            try:
                import errno
                if exception.errno != errno.EEXIST:
                    raise
            finally:
                exception = None
                del exception

        return os.path.join(sPath, sLogName + '.hdf5')


def get_command_line(**kwds):
    """Modified to never use pyinstaller executable when spawning"""
    _python_exe = spawn.get_executable()
    prog = 'from multiprocessing.spawn import spawn_main; spawn_main(%s)'
    prog %= ', '.join(('%s=%r' % item for item in kwds.items()))
    opts = []
    return [
     _python_exe] + opts + ['-c', prog, '--multiprocessing-fork']


def get_preparation_data(basedir, name):
    """Modified to remove information about instrument server"""
    d = spawn._get_preparation_data(name)
    if 'init_main_from_path' in d:
        d.pop('init_main_from_path')
    d.pop('sys_path', None)
    d['dir'] = basedir
    return d


def getDefaultExternalPythonMac():
    prefs = getPreferences()
    appd = prefs.getValue('Application folder')
    if main_is_frozen():
        basedir = os.path.join(appd, 'python-labber')
        basedir = (os.path.exists(basedir) or os.path.join)(get_main_dir(True), 'python-labber')
    else:
        conda_base = os.path.split(os.path.split(os.path.split(sys.executable)[0])[0])[0]
        basedir = os.path.join(conda_base, 'py36-driver')
        if not os.path.exists(basedir):
            py_version = 'py%d%d' % (sys.version_info[0], sys.version_info[1])
            basedir = os.path.expanduser('~/miniconda3/envs/python-labber-%s' % py_version)
        if not os.path.exists(basedir):
            basedir = os.path.expanduser('~/python-labber-%s' % py_version)
    return os.path.join(basedir, 'bin', 'python')


def getDefaultExternalPythonWin(use_32_bit=False):
    prefs = getPreferences()
    appd = prefs.getValue('Application folder')
    if main_is_frozen():
        folder = 'python-labber-32' if use_32_bit else 'python-labber'
        basedir = os.path.join(appd, folder)
    elif use_32_bit:
        basedir = os.path.join(os.path.expanduser('~'), 'Miniconda_32bit', 'envs', 'py35')
    else:
        conda_base = os.path.split(os.path.split(sys.executable)[0])[0]
        basedir = os.path.join(conda_base, 'py36-driver')
    return os.path.join(basedir, 'pythonw.exe')


def startProcess(process, use_default_distribution=False, use_32_bit=False):
    """Configure multiprocessing and start new process"""
    prefs = getPreferences()
    appd = prefs.getValue('Application folder')
    if use_default_distribution:
        path_python = ''
    else:
        path_python = prefs.getValue('Python distribution')
    if use_32_bit:
        if WIN:
            path_python = getDefaultExternalPythonWin(use_32_bit=True)
    if not path_python == '' or MAC or LINUX:
        path_python = getDefaultExternalPythonMac()
    elif WIN:
        path_python = getDefaultExternalPythonWin()
    if path_python == '' or path_python == '.':
        process.start()
    else:
        try:
            oldPath = os.getcwd()
            if not os.path.exists(path_python):
                raise Exception('No python distribution found at:\n%s\n\nPlease update the "Application folder" or the "Python distribution" settings in the Preferences dialog and restart the program.' % path_python)
            spawn.set_executable(path_python)
            if main_is_frozen():
                source_dir = os.path.join(appd, 'python-labber', 'multiproc-include')
            elif MAC:
                source_dir = os.path.join(appd, 'BuildScripts', 'multiproc-include', 'mac')
            elif LINUX:
                source_dir = os.path.join(appd, 'BuildScripts', 'multiproc-include', 'linux')
            else:
                source_dir = os.path.join(appd, 'BuildScripts', 'multiproc-include', 'win')
            py_version = 'py%d%d' % (sys.version_info[0], sys.version_info[1])
            try:
                import subprocess
                py_version = str(subprocess.check_output([path_python, '-c',
                 'import sys; print("py%d%d" % (sys.version_info[0], sys.version_info[1]))']))
                indx = py_version.find('py')
                py_version = py_version[indx:indx + 4]
            except:
                pass

            source_dir = os.path.normpath(os.path.join(source_dir, py_version))
            if not os.path.exists(source_dir):
                raise Exception('No application found at:\n%s\n\nPlease update the "Application folder" settings in the Preferences dialog and restart the program.' % source_dir)
            spawn._get_preparation_data = spawn.get_preparation_data
            spawn.get_preparation_data = lambda x: get_preparation_data(source_dir, x)
            spawn._get_command_line = spawn.get_command_line
            spawn.get_command_line = get_command_line
            os.chdir(source_dir)
            process.start()
        finally:
            os.chdir(oldPath)
            spawn.set_executable(sys.executable)
            if hasattr(spawn, '_get_preparation_data'):
                spawn.get_preparation_data = spawn._get_preparation_data
            if hasattr(spawn, '_get_command_line'):
                spawn.get_command_line = spawn._get_command_line


class DataTypes(object):
    __doc__ = 'Define data types for driver quantities'
    DOUBLE = 0
    BOOLEAN = 1
    COMBO = 2
    STRING = 3
    VECTOR = 4
    COMPLEX = 5
    VECTOR_COMPLEX = 6
    PATH = 7
    BUTTON = 8


class DataAccess(object):
    __doc__ = 'Define data types for driver quantities'
    BOTH = 0
    READ = 1
    WRITE = 2
    NONE = 3


if __name__ == '__main__':
    print(get_main_dir(bGetMainAppPath=True))