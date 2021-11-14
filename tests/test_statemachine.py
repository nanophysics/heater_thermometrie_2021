import logging

import pytest

from pytest_util import TEST_HW_SIMULATE
import micropython_proxy
import heater_wrapper
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity, EnumThermometrie
from micropython_interface import TICK_INTERVAL_S

logger = logging.getLogger("LabberDriver")


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_statemachine(hwserial):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermoff)
    hw.signal(heater_hsm.SignalDefrostSwitchChanged(defrost_on=False))
    hw.let_time_fly(duration_s=5.0)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermoff)

    hw.set_quantity(Quantity.ControlWriteThermometrie, EnumThermometrie.ON)
    hw.let_time_fly(duration_s=5.0)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingoff)

    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.MANUAL)
    hw.let_time_fly(duration_s=5.0)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual)

    hw.set_quantity(Quantity.ControlWriteThermometrie, EnumThermometrie.OFF)
    hw.let_time_fly(duration_s=5.0)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermoff)


class Runner:
    def __init__(self, hw):
        self.hw = hw
        self.next_tick_s = self.time_s = hw.time_now_s

    def run_for(self, duration_s: float):
        end_time_s = self.time_s + duration_s
        while True:
            self.next_tick_s += TICK_INTERVAL_S
            self.hw.sleep(duration_s=self.next_tick_s - self.time_s)
            time_s = self.hw.tick()

            if time_s > end_time_s:
                return


if __name__ == "__main__":
    test_statemachine(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
