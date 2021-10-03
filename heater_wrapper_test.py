import logging

import micropython_proxy
import heater_wrapper

logger = logging.getLogger("LabberDriver")


def doit():
    logger.setLevel(logging.INFO)

    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    hwserial = ""
    ht = heater_wrapper.HeaterWrapper(hwserial=hwserial)
    ht.close()


if __name__ == "__main__":
    doit()
