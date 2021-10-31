import logging

import pytest

from pytest_util import TEST_HW_SIMULATE
from config_all import ONEWIRE_ID_INSERT_NOT_CONNECTED, ONEWIRE_ID_INSERT_UNDEFINED
import micropython_proxy
import heater_wrapper
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity

logger = logging.getLogger("LabberDriver")


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_remove_insert(hwserial):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)
    hw.expect_display(
        """
        |           16.1K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  out of range    |
        |  errors 0        |
"""
    )
    hw.let_time_fly(duration_s=2.0)
    hw.mpi.sim_set_insert_onewire_id(onewire_id=ONEWIRE_ID_INSERT_NOT_CONNECTED)
    hw.let_time_fly(duration_s=2.0)
    hw.expect_state(heater_hsm.HeaterHsm.state_disconnected)
    hw.expect_display(
        """
        |           16.1K  |
        |  DISCONNECTED    |
        |                  |
        |  out of range    |
        |  errors 3        |
"""
    )
    hw.mpi.sim_set_insert_onewire_id(onewire_id=ONEWIRE_ID_INSERT_UNDEFINED)
    hw.let_time_fly(duration_s=2.0)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingoff)
    hw.expect_display(
        """
        |           16.1K  |
        |  HEATING         |
        |  OFF             |
        |  out of range    |
        |  errors 5        |
"""
    )

    hw.close()


if __name__ == "__main__":
    test_remove_insert(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
