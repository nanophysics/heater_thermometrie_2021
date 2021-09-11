# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: Optimizer_Interface.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 19290 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from scipy.optimize import minimize
import numpy as np
from numpy import *
import traceback
from queue import Empty
from inspect import signature
import sys, os, fnmatch, importlib
from collections import OrderedDict
import ScriptsAndSettings, copy, SG_Preferences

class OptimizerParseError(Exception):
    pass


class Error(Exception):
    __doc__ = 'Base error for optimizer'


class Completed(Exception):
    __doc__ = 'Exception raised when optimizer completes operation'

    def __init__(self, result):
        """Store optimizer results in exception"""
        self.result = result

    def get_results(self):
        """Return results from optimizer"""
        return self.result


class Abort(Exception):
    __doc__ = 'Exception for aborting optimizer, but keeping process alive'


class Terminate(Exception):
    __doc__ = 'Exception for aborting optimizer and terminating process'


class NotResponding(Exception):
    __doc__ = 'Exception in case of optimizer process not responding'


def startOptimizer(queue_in=None, queue_out=None):
    """Helper function for starting up the optimizer process"""
    optimizer = LabberOptimizer(queue_in, queue_out)
    optimizer.main_loop()


def scan_for_optimizers(folder, raise_error=True):
    """Scan for optimizers in given folder"""
    optimizers = {}
    optimizer_settings = {}
    if not os.path.exists(folder):
        return (optimizers, optimizer_settings)
    files = os.listdir(folder)
    py_files = fnmatch.filter(files, '*.[pP][yY]')
    error_string = None
    if folder not in sys.path:
        sys.path.append(folder)
    for py_file in py_files:
        full_path = os.path.join(folder, py_file)
        try:
            name = os.path.splitext(py_file)[0]
            module = importlib.import_module(name)
            module = importlib.reload(module)
            if hasattr(module, 'optimize'):
                sig = signature(module.optimize)
                if len(sig.parameters) == 2:
                    if 'config' in sig.parameters:
                        if 'minimize_function' in sig.parameters:
                            if hasattr(module, 'define_optimizer_settings'):
                                cfg = module.define_optimizer_settings()
                                updated_items = []
                                for item in cfg:
                                    temp = SG_Preferences.PrefsItem(item)
                                    updated_items.append(temp.getConfigAsDict())

                                settings = SG_Preferences.Preferences(name='Measurement',
                                  lDictItem=updated_items)
                                base = 'opt-' + name + ': '
                                for d in updated_items:
                                    d['label'] = d['name']
                                    d['name'] = base + d['name']
                                    d['section'] = 'Optimizer'
                                    d['group'] = name
                                    if d.get('state_item', None) is None:
                                        d['state_item'] = 'Method'
                                        d['state_values'] = [name]
                                    else:
                                        d['state_item'] = base + d['state_item']

                                optimizer_settings[name] = updated_items
                            else:
                                optimizers[name] = module
                            continue
            error_string = 'Optimizer function not properly defined for ' + 'file:\n%s' % str(full_path)
        except Exception as e:
            try:
                error_string = 'Optimizer function not properly defined for file:\n' + str(full_path) + '\n\n' + traceback.format_exc()
            finally:
                e = None
                del e

    if raise_error:
        if error_string is not None:
            raise OptimizerParseError(error_string)
    return (
     optimizers, optimizer_settings)


def get_dict_with_optimizers(main_folder=None, local_folder=None, raise_error=True):
    """Check the optimizer folders and return a list of dict with name/path"""
    if main_folder is None:
        preferences = ScriptsAndSettings.getPreferences()
        main_folder = preferences.getValue('Optimizer functions')
    if local_folder is None:
        preferences = ScriptsAndSettings.getPreferences()
        local_folder = preferences.getValue('Local optimizers')
    main_opt, main_cfg = scan_for_optimizers(main_folder, raise_error)
    local_opt, local_cfg = scan_for_optimizers(local_folder, raise_error)
    for name, optimizer in local_opt.items():
        main_opt[name] = optimizer

    for name, optimizer_cfg in local_cfg.items():
        main_cfg[name] = optimizer_cfg

    output = OrderedDict()
    for key in sorted(main_opt.keys()):
        output[key] = main_opt[key]

    return (output, main_cfg)


class LabberOptimizer(object):
    __doc__ = 'Object for running optimizer in Labber measurement'

    def __init__(self, queue_in, queue_out):
        """Store queues and optimizer config in object"""
        self.queue_in = queue_in
        self.queue_out = queue_out
        self.interface = InterfaceToLabber(queue_in, queue_out)
        self.minimize_code = None
        self.optimizers = get_dict_with_optimizers(raise_error=False)[0]

    def main_loop(self):
        """Main loop of optimizer"""
        while 1:
            try:
                data = self.interface.wait_for_data()
                if data['operation'] == Interface.START:
                    self.interface.report_ok_status()
                    self.config = data['data']
                    channels = self.config['optimizer_channels']
                    self.low_lim = np.array([d['Min value'] for d in channels])
                    self.high_lim = np.array([d['Max value'] for d in channels])
                    code = self.config['Minimization function'].strip()
                    if len(code) > 0:
                        self.minimize_code = compile(code, '<string>', 'eval')
                    else:
                        self.minimize_code = None
                    method = self.config['Method']
                    if method not in self.optimizers:
                        self.optimizers = get_dict_with_optimizers(raise_error=False)[0]
                        if method not in self.optimizers:
                            self.interface.raise_error('Optimizer "%s" is not available.' % method)
                            continue
                    module = self.optimizers[method]
                    try:
                        importlib.reload(module)
                    except Exception:
                        self.interface.raise_error('Optimizer named %s is not available.' % method)
                        continue

                    scaled_config = self.get_normalized_configuration()
                    res = module.optimize(scaled_config, self.evaluate_function)
                    try:
                        res[x] = self.scale_parameters_to_labber(res[x])
                    except Exception:
                        pass

                    self.interface.report_final_result(res)
                else:
                    msg = 'Unexpected data received:\n\n' + str(data.get('data', ''))
                    self.interface.raise_error(msg)
            except Completed as e:
                try:
                    self.interface.report_final_result(e.get_results())
                finally:
                    e = None
                    del e

            except Terminate:
                return
            except Abort:
                pass
            except Exception as e:
                try:
                    msg = traceback.format_exc()
                    self.interface.raise_error(msg)
                finally:
                    e = None
                    del e

    def evaluate_function(self, parameters):
        """Ask Labber to measure at given parameter values.

        Parameters
        ----------
        parameters : numpy array
            Parameter values determined by the optimizer.

        Returns
        -------
        list or numpy array
            Measured data from Labber.

        """
        x = np.array(parameters, copy=False)
        x = self.scale_parameters_to_labber(x)
        np.clip(x, (self.low_lim), (self.high_lim), out=x)
        self.interface.evaluate(x)
        y = self.interface.wait_for_evaluation()
        if self.minimize_code is None:
            return y[0]
        value = eval(self.minimize_code)
        if value < self.config['Target value']:
            res = dict(message='Terminated after reaching absolute target',
              success=True,
              x=x,
              fun=value)
            raise Completed(res)
        else:
            return value

    def get_normalized_configuration(self):
        """Get copy of optimizer config with parameter scaled if necessary"""
        scaled_config = copy.deepcopy(self.config)
        x_tolerance = np.array([d['Precision'] for d in self.config['optimizer_channels']])
        if True or (np.all(x_tolerance == x_tolerance[0])):
            self.scaling = np.ones_like(x_tolerance)
            return scaled_config
        self.scaling = x_tolerance / min(x_tolerance)
        for n, channel in enumerate(scaled_config['optimizer_channels']):
            channel['Start value'] /= self.scaling[n]
            channel['Initial step size'] /= self.scaling[n]
            channel['Min value'] /= self.scaling[n]
            channel['Max value'] /= self.scaling[n]
            channel['Precision'] /= self.scaling[n]

        return scaled_config

    def scale_parameters_to_labber(self, x):
        """Scale normalized optimizer parameters to actual labber values"""
        return x * self.scaling


class Interface(object):
    __doc__ = 'Helper object for interfacing data between the optimizer and Labber'
    START = 0
    EVALUATE = 1
    REPORT = 2
    ERROR = 3
    ABORT = 4
    COMPLETED = 5
    TERMINATE = 6
    STATUS_OK = 7

    def __init__(self, queue_to_optimizer, queue_from_optimizer):
        super(Interface, self).__init__()
        self._queue_to_optimizer = queue_to_optimizer
        self._queue_from_optimizer = queue_from_optimizer
        self.queue_send = None
        self.queue_receive = None

    def _set_interface_direction(self, running_in_optimizer=True):
        """Set queues to reflect interface direction"""
        if running_in_optimizer:
            self.queue_send = self._queue_from_optimizer
            self.queue_receive = self._queue_to_optimizer
        else:
            self.queue_send = self._queue_to_optimizer
            self.queue_receive = self._queue_from_optimizer

    def _send_data(self, operation, data=None):
        """Send data over queues"""
        if operation in (Interface.ABORT, Interface.TERMINATE, Interface.ERROR):
            self.flush_queues()
        d = dict(operation=operation,
          data=data)
        self.queue_send.put(d)

    def flush_queues(self):
        """Flush both queues"""
        for queue in [self.queue_send, self.queue_receive]:
            while True:
                try:
                    queue.get_nowait()
                except Exception:
                    break

    def wait_for_data(self, timeout=None):
        """Wait for data from queue.

        Parameters
        ----------
        timeout : float
            Timeout before returning error when waiting for response.

        Returns
        -------
        dict
            Data received over queue, with keys 'data' and 'operation'

        """
        try:
            d = self.queue_receive.get(block=True, timeout=None)
        except Empty:
            raise NotResponding()

        if d['operation'] == Interface.ABORT:
            raise Abort()
        if d['operation'] == Interface.TERMINATE:
            raise Terminate()
        if d['operation'] == Interface.ERROR:
            raise Error(str(d['data']))
        if d['operation'] == Interface.COMPLETED:
            raise Completed(d['data'])
        return d

    def raise_error(self, message=''):
        """Send error over queue."""
        self._send_data(self.ERROR, message)


class InterfaceToLabber(Interface):
    __doc__ = 'Interface from optimizer to Labber'

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self._set_interface_direction(running_in_optimizer=True)

    def report_ok_status(self):
        """Report status of optimizer process, to confirm operation.

        """
        self._send_data(self.STATUS_OK)

    def report_final_result(self, optimizer_result):
        """Report final result from optimizer to Labber.

        Parameters
        ----------
        optimizer_result : dict
            Results from optimizer.

        """
        self._send_data(self.COMPLETED, optimizer_result)

    def evaluate(self, values):
        """Ask Labber to measure at given parameter values.

        Parameters
        ----------
        values : numpy array
            Parameter values determined by the optimizer.

        """
        self._send_data(self.EVALUATE, values)

    def wait_for_evaluation(self):
        """Wait for Labber to return measured data.

        Returns
        -------
        list or numpy array
            Measured data from Labber.

        """
        d = self.wait_for_data()
        return d['data']


class InterfaceToOptimizer(Interface):
    __doc__ = 'Interface from Labber to optimizer'

    def __init__(self, *args, **kwargs):
        (super().__init__)(*args, **kwargs)
        self._set_interface_direction(running_in_optimizer=False)

    def start_optimizer(self, config, timeout=5.0):
        """Start optimzer for given optimizer configuration

        Parameters
        ----------
        config : dict
            Optimizer settings provided from the measurement configuration.

        timeout : float
            Timeout before returning error when waiting for response.

        """
        self._send_data(self.START, config)
        response = self.wait_for_data(timeout=timeout)
        if response.get('operation') != self.STATUS_OK:
            self.abort()
            raise NotResponding()

    def abort(self):
        """Send abort request to optimizer."""
        self._send_data(self.ABORT)

    def terminate(self):
        """Send abort request to optimizer."""
        self._send_data(self.TERMINATE)

    def report_data(self, measured_values):
        """Report measured data from Labber to optimizer.

        Parameters
        ----------
        measured_values : list or numpy array
            Measured values from last round of Labber measurement.

        """
        self._send_data(self.REPORT, measured_values)

    def wait_for_parameters(self):
        """Wait for optimizer to provide new parameters.

        Returns
        -------
        numpy array
            New parameter values from optimizer.

        """
        d = self.wait_for_data()
        return d['data']


if __name__ == '__main__':
    dd = get_dict_with_optimizers(os.path.expanduser('~/Dropbox (Personal)/Python/Labber/Script/Optimizers'), os.path.expanduser('~/Dropbox (Personal)/Python/Labber/Script/Optimizers'))[0]
    print(dd)
    print([l for l in dd.keys()])