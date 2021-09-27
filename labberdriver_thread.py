import time
import wrapt
import logging
import threading

import labberdriver_wrapper

logger = logging.getLogger("heater_thermometrie_2012")

LOCK = threading.Lock()

def synchronized(lock):
    # See: https://wrapt.readthedocs.io/en/latest/examples.html
    # Alternative implementation: https://de.slideshare.net/GrahamDumpleton/implementing-a-decorator-for-thread-synchronisation
    @wrapt.decorator
    def _wrapper(wrapped, _instance, args, kwargs):
        with lock:
            try:
                return wrapped(*args, **kwargs)
            except:  # pylint: disable=bare-except
                logger.exception(
                    'Exception in method "FlaskEnvironmentWrapper.%s"', wrapped.__name__
                )
                raise

    return _wrapper

class LabberDriverThread(threading.Thread):
    def __init__(self, hwserial: str):
        logger.info(f"LabberDriverThread(hwserial='{hwserial}')")
        super().__init__(daemon=True)
        self.ldw = labberdriver_wrapper.LabberDriverWrapper(hwserial=hwserial)
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

    @synchronized(LOCK)
    def _tick(self):
        print("Tick")

    @synchronized(LOCK)
    def set_value(self, name:str, value):
        self.ldw.set_value(name=name, value=value)

    @synchronized(LOCK)
    def get_value(self, name:str):
        return self.ldw.get_value(name=name)
