import logging

import micropython_proxy
import heater_thread
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity, EnumThermometrie

logger = logging.getLogger("LabberDriver")


def test_a():
    logger.setLevel(logging.INFO)

    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    ht = heater_thread.HeaterThread(hwserial=hwserial)
    ht.signal(heater_hsm.SignalDefrostSwitchChanged(on=False))
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon)

    ht.set_value(Quantity.ControlWriteThermometrie, EnumThermometrie.ON)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon)

    ht.set_value(Quantity.ControlWriteHeating, EnumHeating.MANUAL)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual)
