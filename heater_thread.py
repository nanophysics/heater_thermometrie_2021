import os
import time
import logging
import threading

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
        self.hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)
        self._stopping = False
        self.start()

    def run(self):
        while not self._stopping:
            try:
                self._tick()
            except serial.serialutil.SerialException as ex:
                logger.fatal(
                    f"Probably, the USB cable to the heater_thermometrie_2021 was disconnected: {repr(ex)}"
                )
                os._exit(42)
                return
            except Exception as ex:  # pylint: disable=broad-except
                logger.exception(ex)
            time.sleep(1.0)

    def stop(self):
        self._stopping = True
        self.join(timeout=10.0)

    @synchronized
    def _tick(self):
        self.hw.tick()

    @synchronized
    def set_value(self, name: str, value):
        return self.hw.set_value(name=name, value=value)

    @synchronized
    def set_quantity(self, quantity: Quantity, value):
        return self.hw.set_quantity(quantity=quantity, value=value)

    @synchronized
    def get_value(self, name: str):
        return self.hw.get_value(name=name)

    @synchronized
    def signal(self, signal):
        self.hw.signal(signal)

    @synchronized
    def expect_state(self, expected_meth):
        self.hw.expect_state(expected_meth=expected_meth)
