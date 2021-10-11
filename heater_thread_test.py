import time
import logging

import micropython_proxy
import heater_thread
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity, EnumThermometrie

logger = logging.getLogger("LabberDriver")


def doit():
    logger.setLevel(logging.INFO)

    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    hwserial = ""
    ht = heater_thread.HeaterThread(hwserial=hwserial)
    time.sleep(1.5)
    ht.signal(heater_hsm.SignalDefrostSwitchChanged(on=False))
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon)

    ht.set_value(Quantity.Thermometrie, EnumThermometrie.ON)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon)

    ht.set_value(Quantity.Heating, EnumHeating.MANUAL)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual)

    ht.set_value(Quantity.Heating, EnumHeating.CONTROLLED)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)

    ht.set_value(Quantity.Thermometrie, EnumThermometrie.OFF)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermoff)

    ht.signal(heater_hsm.SignalDefrostSwitchChanged(on=True))
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_defrost)

    ht.set_value(Quantity.Heating, EnumHeating.CONTROLLED)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_defrost)

    ht.signal(heater_hsm.SignalInsertSerialChanged(serial=None))
    ht.expect_state(heater_hsm.HeaterHsm.state_disconnected)

    ht.set_value(Quantity.Heating, EnumHeating.CONTROLLED)
    ht.expect_state(heater_hsm.HeaterHsm.state_disconnected)

    time.sleep(200.0)
    ht.stop()


if __name__ == "__main__":
    doit()
