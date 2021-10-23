import logging

import pytest

from pytest_util import TEST_HW_SIMULATE
import micropython_proxy
import heater_wrapper
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity

logger = logging.getLogger("LabberDriver")


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_controller(hwserial):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)

    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)

    hw.set_quantity(Quantity.ControlWriteTemperature, 42.0)

    hw.let_time_fly(duration_s=20.0)


if __name__ == "__main__":
    test_controller(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
