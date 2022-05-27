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
        import debugpy  # pylint: disable=import-error

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
        self.dict_values_labber_thread_copy = {}
        super().__init__(daemon=True)
        self._hw = heater_wrapper.HeaterWrapper(hwserial=hwserial, force_use_realtime_factor=force_use_realtime_factor)
        self._stopping = False
        self.start()

    def run(self):
        while not self._stopping:
            start_s = self._hw.time_now_s
            try:
                self._tick()
            except serial.serialutil.SerialException as ex:
                logger.fatal(f"Probably, the USB cable to the heater_thermometrie_2021 was disconnected: {repr(ex)}")
                os._exit(42)
                return
            except Exception as ex:  # pylint: disable=broad-except
                logger.exception(ex)

            elapsed_s = self._hw.time_now_s - start_s
            sleep_s = TICK_INTERVAL_S - elapsed_s
            if sleep_s > 0.0:
                logger.debug(f"sleep_s:{sleep_s:0.3f}s")
                self._hw.sleep(sleep_s)

    def stop(self):
        self._stopping = True
        self.join(timeout=10.0 * TICK_INTERVAL_S)

    @synchronized
    def _tick(self) -> None:
        self._hw.tick()
        # Create a copy of all values to allow access for the labber thread without any delay.
        self.dict_values_labber_thread_copy = self._hw.dict_values.copy()

    @synchronized
    def set_quantity_sync(self, quantity: Quantity, value):
        return self._hw.set_quantity(quantity=quantity, value=value)

    @synchronized
    def _is_settled(self):
        return self._hw.hsm_heater.is_settled()

    def set_value(self, name: str, value):
        assert isinstance(name, str)
        quantity = Quantity(name)

        if quantity == Quantity.ControlWriteTemperatureAndSettle_K:
            return self._set_temperature_and_settle(quantity=quantity, value=value)

        # logger.info(f"set_value_A('{name}', '{value}'): {quantity}")
        value_new = self.set_quantity_sync(quantity=quantity, value=value)
        # logger.info(f"set_value_B('{name}', '{value}'): {quantity} -> rc: {value_new!r}")
        return value_new

    def _set_temperature_and_settle(self, quantity: Quantity, value: float):
        assert quantity == Quantity.ControlWriteTemperatureAndSettle_K

        def block_until_settled():
            tick_count_before = self._hw.tick_count
            timeout_s = self._hw.time_now_s + self._hw.get_quantity(Quantity.ControlWriteTimeoutTime_S)
            while True:
                self._hw.sleep(TICK_INTERVAL_S / 2.0)
                if tick_count_before == self._hw.tick_count:
                    # Wait for a tick to make sure that the statemachine was called at least once
                    continue
                if not self._hw.hsm_heater.is_state(HeaterHsm.state_connected_thermon_heatingcontrolled):
                    # Unexpected state change
                    logger.info(f"Waiting for 'ControlWriteTemperatureAndSettle_K'. Unexpected state change. Got '{self._hw.hsm_heater._state_actual}'!")
                    return
                if self._is_settled():
                    return
                if self._hw.time_now_s > timeout_s:
                    logger.info("Timeout while 'ControlWriteTemperatureAndSettle_K'")
                    return

        if abs(value - heater_wrapper.TEMPERATURE_SETTLE_OFF_K) < 1.0e-9:
            logger.warning(f"'{quantity.value}' set to {value:0.1f} K: SKIPPED")
            return

        self._hw.set_quantity(Quantity.ControlWriteTemperature_K, value)
        self._hw.hsm_heater.wait_temperature_and_settle_start()
        logger.warning(f"'{quantity.value}' set to {value:0.1f} K: Blocking. Timout = {self._hw.get_quantity(Quantity.ControlWriteTimeoutTime_S)}s")
        block_until_settled()
        self._hw.hsm_heater.wait_temperature_and_settle_over()
        logger.warning("Settle/Timeout time over")
        return heater_wrapper.TEMPERATURE_SETTLE_OFF_K

    @synchronized
    def set_quantity(self, quantity: Quantity, value):
        return self._hw.set_quantity(quantity=quantity, value=value)

    def get_value(self, name: str):
        """
        This typically returns immedately as it accesses a copy of all values.
        Only in rare cases, it will delay for max 0.5s.
        """
        assert isinstance(name, str)
        quantity = Quantity(name)
        try:
            return self.dict_values_labber_thread_copy[quantity]
        except KeyError:
            # Not all values are stored in the dictionary.
            # In this case we have to use the synchronized call.
            return self.get_quantity_synchronized(quantity=quantity)

    @synchronized
    def get_quantity_synchronized(self, quantity: Quantity):
        return self._hw.get_quantity(quantity=quantity)

    @synchronized
    def signal(self, signal):
        self._hw.signal(signal)

    @synchronized
    def expect_state(self, expected_meth):
        self._hw.expect_state(expected_meth=expected_meth)
