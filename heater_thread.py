import os
import logging
import threading
import itertools

import serial

import heater_wrapper
from heater_driver_utils import Quantity

logger = logging.getLogger("LabberDriver")

LOCK = threading.Lock()

try:
    if False:
        import debugpy

        debugpy.listen(5678)
        debugpy.wait_for_client()
        debugpy.breakpoint()
except ModuleNotFoundError:
    pass


def synchronized(func):
    def wrapper(*args, **kwargs):
        with LOCK:
            try:
                return func(*args, **kwargs)
            except:  # pylint: disable=bare-except
                logger.exception('Exception in method "HeaterThread.%s"', func.__name__)
                raise

    return wrapper


class HeaterThread(threading.Thread):
    def __init__(self, hwserial: str):
        logger.info(f"HeaterThread(hwserial='{hwserial}')")
        super().__init__(daemon=True)
        self._hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)
        self._stopping = False
        self.start()

    def run(self):
        while not self._stopping:
            try:
                self._tick()
            except serial.serialutil.SerialException as ex:
                logger.fatal(f"Probably, the USB cable to the heater_thermometrie_2021 was disconnected: {repr(ex)}")
                os._exit(42)
                return
            except Exception as ex:  # pylint: disable=broad-except
                logger.exception(ex)
            self._hw.sleep(1.0)

    def stop(self):
        self._stopping = True
        self.join(timeout=10.0)

    @synchronized
    def _tick(self):
        self._hw.tick()

    @synchronized
    def set_quantity_sync(self, quantity: Quantity, value):
        return self._hw.set_quantity(quantity=quantity, value=value)

    @synchronized
    def _temperature_settled(self):
        return self._hw.hsm_heater.temperature_settled()

    def set_value(self, name: str, value):
        assert isinstance(name, str)
        quantity = Quantity(name)
        rc = self.set_quantity_sync(quantity=quantity, value=value)

        if quantity == Quantity.ControlWriteTemperatureAndWait:
            time_start_s = next_log_s = self._hw.time_now_s
            while True:
                self._hw.sleep(0.5)
                settled = self._temperature_settled()
                if self._hw.time_now_s > next_log_s:
                    logger.info(f"Waiting for 'ControlWriteTemperatureAndWait'. {self._hw.time_now_s-time_start_s:0.1f}s: settled={settled}")
                    next_log_s += 5
                if settled:
                    return rc
        return rc

    @synchronized
    def set_quantity(self, quantity: Quantity, value):
        return self._hw.set_quantity(quantity=quantity, value=value)

    @synchronized
    def get_value(self, name: str):
        return self._hw.get_value(name=name)

    @synchronized
    def signal(self, signal):
        self._hw.signal(signal)

    @synchronized
    def expect_state(self, expected_meth):
        self._hw.expect_state(expected_meth=expected_meth)
