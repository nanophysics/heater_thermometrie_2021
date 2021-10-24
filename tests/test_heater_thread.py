import logging
import pytest

from pytest_util import TEST_HW_SIMULATE
import micropython_proxy
import heater_thread
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity, EnumThermometrie
from config_all import ONEWIRE_ID_INSERT_NOT_CONNECTED

logger = logging.getLogger("LabberDriver")

@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_heater_thread_run_200s(hwserial):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    ht = heater_thread.HeaterThread(hwserial=hwserial)
    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    logger.info("Now sleeping for 200.0s")
    ht._hw.sleep(200.0)
    ht.stop()

@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_heater_thread(hwserial):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    ht = heater_thread.HeaterThread(hwserial=hwserial)
    ht._hw.sleep(1.5)
    ht.signal(heater_hsm.SignalDefrostSwitchChanged(on=False))
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingoff)

    ht.set_quantity(Quantity.ControlWriteThermometrie, EnumThermometrie.ON)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon)

    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.MANUAL)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual)

    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)

    ht.set_quantity(Quantity.ControlWriteThermometrie, EnumThermometrie.OFF)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermoff)

    ht.signal(heater_hsm.SignalDefrostSwitchChanged(on=True))
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_defrost)

    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_defrost)

    ht.signal(heater_hsm.SignalInsertSerialChanged(onewire_id=ONEWIRE_ID_INSERT_NOT_CONNECTED))
    ht.expect_state(heater_hsm.HeaterHsm.state_disconnected)

    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    ht.expect_state(heater_hsm.HeaterHsm.state_disconnected)

    logger.info("Now sleeping for 200.0s")
    ht._hw.sleep(200.0)
    ht.stop()


if __name__ == "__main__":
    test_heater_thread(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
