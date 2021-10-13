import logging

import micropython_proxy
import heater_wrapper
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity

logger = logging.getLogger("LabberDriver")

INTERVAL_S = 1.0


def test_controller_a():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    hwserial = ""
    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)

    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)

    hw.mpi.fe.sim_set_voltage(carbon=True, value=1.6)

    hw.get_quantity(Quantity.ControlWriteTemperature)
    hw.set_quantity(Quantity.ControlWriteTemperature, 42.0)

    next_tick_s = time_s = hw.time_now_s
    while True:
        next_tick_s += INTERVAL_S
        hw.sleep(duration_s=next_tick_s - time_s)
        time_s = hw.tick()

        if time_s > 20:
            return

if __name__ == "__main__":
    test_controller_a()
