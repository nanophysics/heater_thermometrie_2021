import time
import micropython_proxy
import labberdriver_thread


def doit():
    hwserial = ""
    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    ldt = labberdriver_thread.LabberDriverThread(hwserial=hwserial)
    time.sleep(4.0)
    ldt.stop()


if __name__ == "__main__":
    doit()
