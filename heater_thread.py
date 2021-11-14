import os
import logging
import threading

import serial
from heater_hsm import HeaterHsm
from micropython_interface import TICK_INTERVAL_S

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
    def __init__(self, hwserial: str, force_use_realtime_factor: float = None):
        logger.info(f"HeaterThread(hwserial='{hwserial}')")
        super().__init__(daemon=True)
        self._hw = heater_wrapper.HeaterWrapper(hwserial=hwserial, force_use_realtime_factor=force_use_realtime_factor)
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
            self._hw.sleep(TICK_INTERVAL_S)

    def stop(self):
        self._stopping = True
        self.join(timeout=10.0 * TICK_INTERVAL_S)

    @synchronized
    def _tick(self):
        self._hw.tick()

    @synchronized
    def set_quantity_sync(self, quantity: Quantity, value):
        return self._hw.set_quantity(quantity=quantity, value=value)

    @synchronized
    def _is_settled(self):
        return self._hw.hsm_heater.is_settled()

    def set_value(self, name: str, value):
        assert isinstance(name, str)
        quantity = Quantity(name)

        if quantity == Quantity.ControlWriteTemperatureAndSettle:

            def block_until_settled():
                tick_count_before = self._hw.tick_count
                timeout_s = self._hw.time_now_s + self._hw.get_quantity(Quantity.ControlWriteTimeoutTime)
                while True:
                    self._hw.sleep(TICK_INTERVAL_S / 2.0)
                    if tick_count_before == self._hw.tick_count:
                        # Wait for a tick to make sure that the statemachine was called at least once
                        continue
                    if not self._hw.hsm_heater.is_state(HeaterHsm.state_connected_thermon_heatingcontrolled):
                        # Unexpected state change
                        logger.info(f"Waiting for 'ControlWriteTemperatureAndSettle'. Unexpected state change. Got '{self._hw.hsm_heater._state_actual}'!")
                        return
                    if self._is_settled():
                        return
                    if self._hw.time_now_s > timeout_s:
                        logger.info("Timeout while 'ControlWriteTemperatureAndSettle'")
                        return

            self._hw.set_quantity(Quantity.ControlWriteTemperature, value)
            self._hw.hsm_heater.wait_temperature_and_settle_start()
            block_until_settled()
            self._hw.hsm_heater.wait_temperature_and_settle_over()
            return heater_wrapper.TEMPERATURE_SETTLE_K

        # logger.info(f"set_value_A('{name}', '{value}'): {quantity}")
        value_new = self.set_quantity_sync(quantity=quantity, value=value)
        # logger.info(f"set_value_B('{name}', '{value}'): {quantity} -> rc: {value_new!r}")
        return value_new

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
