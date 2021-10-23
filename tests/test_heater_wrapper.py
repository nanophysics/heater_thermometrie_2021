import logging

import pytest

from pytest_util import TEST_HW_SIMULATE
import micropython_proxy
import heater_wrapper

logger = logging.getLogger("LabberDriver")



@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_doit(hwserial):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    ht = heater_wrapper.HeaterWrapper(hwserial=hwserial)
    ht.close()


if __name__ == "__main__":
    test_doit(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
