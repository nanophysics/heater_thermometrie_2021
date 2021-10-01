import time
import logging
import threading

import heater_wrapper

logger = logging.getLogger("heater_thermometrie_2012")

LOCK = threading.Lock()


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
            except Exception as ex:
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
        self.hw.set_value(name=name, value=value)

    @synchronized
    def get_value(self, name: str):
        return self.hw.get_value(name=name)
