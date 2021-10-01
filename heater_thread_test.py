import time
import micropython_proxy
import heater_thread


def doit():
    hwserial = ""
    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    ht = heater_thread.HeaterThread(hwserial=hwserial)
    time.sleep(4.0)
    ht.stop()


if __name__ == "__main__":
    doit()
