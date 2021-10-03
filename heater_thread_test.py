import time
import micropython_proxy
import heater_thread
from heater_driver_utils import Quantity, EnumThermometrie


def doit():
    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    hwserial = ""
    ht = heater_thread.HeaterThread(hwserial=hwserial)
    time.sleep(2.0)
    ht.set_value(Quantity.Thermometrie, EnumThermometrie.ON)
    time.sleep(2.0)
    ht.set_value(Quantity.Thermometrie, EnumThermometrie.OFF)
    time.sleep(200.0)
    ht.stop()


if __name__ == "__main__":
    doit()
