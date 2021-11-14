import logging

import pytest

from pytest_util import TEST_HW_SIMULATE
import micropython_proxy
import heater_wrapper
import heater_hsm
from heater_driver_utils import EnumHeating, EnumThermometrie, Quantity

logger = logging.getLogger("LabberDriver")


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_controller(hwserial):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)

    hw.set_quantity(Quantity.ControlWriteThermometrie, EnumThermometrie.ON)
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.let_time_fly(duration_s=5.0)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)

    hw.set_quantity(Quantity.ControlWriteTemperature, 42.0)
    hw.sim_reset_error_counter()

    hw.let_time_fly(duration_s=10.0)
    hw.expect_display(
        """
        | ? |
        |  HEATING         |
        |  CONTROLLED      |
        |  out of range    |
        | ? |
    """
    )

    hw.let_time_fly(duration_s=10.0)
    hw.expect_display(
        """
        | ? |
        |  HEATING         |
        |  CONTROLLED      |
        |  out of range    |
        | ? |
    """
    )

    hw.let_time_fly(duration_s=100.0)
    hw.expect_display(
        """
        | ? |
        |  HEATING         |
        |  CONTROLLED      |
        | ? |
        | ? |
    """
    )


if __name__ == "__main__":
    test_controller(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
