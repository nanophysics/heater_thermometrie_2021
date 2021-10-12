import logging

import micropython_proxy
import heater_wrapper
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity

logger = logging.getLogger("LabberDriver")


def test_a():
    logger.setLevel(logging.INFO)

    hwserial = ""
    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)

    hw.set_value(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)

    hw.mpi.fe.sim_set_voltage(carbon=True, value=1.6)

    hw.get_value(Quantity.ControlWriteTemperature)
