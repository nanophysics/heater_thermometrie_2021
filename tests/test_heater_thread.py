import logging
import pytest

import test_settletime
from micropython_interface import TICK_INTERVAL_S

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

    ht = heater_thread.HeaterThread(hwserial=hwserial, force_use_realtime=True)
    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    logger.info("Now sleeping for 200.0s")
    ht._hw.sleep(200.0)
    ht.stop()


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_heater_thread(hwserial, force_use_realtime=True):
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

    ht.signal(
        heater_hsm.SignalInsertSerialChanged(onewire_id=ONEWIRE_ID_INSERT_NOT_CONNECTED)
    )
    ht.expect_state(heater_hsm.HeaterHsm.state_disconnected)

    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    ht.expect_state(heater_hsm.HeaterHsm.state_disconnected)

    logger.info("Now sleeping for 200.0s")
    ht._hw.sleep(200.0)
    ht.stop()


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_control_and_settle(hwserial):
    """
    Combobox heating controlled
    Now ControlWriteTemperatureAndSettle
    Verify that timeout time starts from 0
    """
    logging.basicConfig()
    logger.setLevel(logging.DEBUG)

    ht = heater_thread.HeaterThread(hwserial=hwserial, force_use_realtime=True)
    ht.set_quantity(
        Quantity.ControlWriteTemperature, test_settletime.TEMPERATURE_SET40_K
    )
    ht.set_quantity(Quantity.ControlWriteTemperatureToleranceBand, 1.0)
    ht.set_quantity(Quantity.ControlWriteSettleTime, test_settletime.SETTLE_TIME_S)
    ht.set_quantity(Quantity.ControlWriteTimeoutTime, test_settletime.TIMEOUT_TIME_S)
    ht._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=40.5)

    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    ht._hw.let_time_fly(duration_s=1.0)

    before_s = ht._hw.time_now_s
    ht.set_value(
        Quantity.ControlWriteTemperatureAndSettle.value,
        test_settletime.TEMPERATURE_SET40_K,
    )
    duration_s = ht._hw.time_now_s - before_s
    assert (
        test_settletime.SETTLE_TIME_S - 1.0 - 2.0
        < duration_s
        < test_settletime.SETTLE_TIME_S - 1.0 + 2.0
    )
    assert ht._hw.hsm_heater.error_counter == 0
    assert ht._hw.hsm_heater.is_settled()
    assert ht._hw.hsm_heater.is_inrange()

    #
    # Now with new set_temperature out of range -> Timeout
    #
    before_s = ht._hw.time_now_s
    ht.set_value(
        Quantity.ControlWriteTemperatureAndSettle.value,
        test_settletime.TEMPERATURE_SET42_K,
    )
    duration_s = ht._hw.time_now_s - before_s
    assert (
        test_settletime.TIMEOUT_TIME_S - 5.0
        < duration_s
        < test_settletime.TIMEOUT_TIME_S + 5.0
    )
    assert not ht._hw.hsm_heater.is_inrange()
    assert not ht._hw.hsm_heater.is_settled()
    assert 0 <= ht._hw.hsm_heater.error_counter <= 2

    ht._hw.expect_display("""
        |           40.5K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  out of range    |
        |  errors 0        |
""")

    tick_count_before = ht._hw.tick_count
    while ht._hw.tick_count < tick_count_before + 2:
        ht._hw.sleep(TICK_INTERVAL_S / 5.0)
    ht._hw.expect_display("""
        |           40.5K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  out of range    |
        |  errors 2        |
""")


if __name__ == "__main__":
    test_control_and_settle(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
    # test_heater_thread(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
