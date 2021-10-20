import logging

import pytest
import micropython_proxy
import heater_wrapper
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity

logger = logging.getLogger("LabberDriver")


@pytest.mark.parametrize("hwserial", ["", micropython_proxy.HWSERIAL_SIMULATE])
def test_settletime(hwserial):
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)

    # Prepare Settle Test
    hw.set_quantity(Quantity.ControlWriteTemperature, 42.0)
    hw.set_quantity(Quantity.ControlWriteTemperatureToleranceBand, 2.0)
    hw.set_quantity(Quantity.ControlWriteTimeoutTime, 100.0)
    hw.set_quantity(Quantity.ControlWriteSettleTime, 10.0)

    #
    # Start controller - Settle Time Test
    #
    hw.mpi.sim_set_voltage(carbon=True, value=1.6)
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)
    assert not hw.hsm_heater.settled
    assert not hw.hsm_heater.timeout

    # Wait with temperature outside range
    hw.let_time_fly(duration_s=10.0)
    assert not hw.hsm_heater.settled
    assert not hw.hsm_heater.timeout
    hw.mpi.sim_set_voltage(carbon=True, value=42.0)
    eca = hw.error_counter_assertion

    # Temperature inside range: Settle time starts
    hw.let_time_fly(duration_s=9.5)
    # Settle time is NOT over
    assert not hw.hsm_heater.settled
    assert not hw.hsm_heater.timeout
    eca.assert_no_errors("Temperature is in range")
    hw.let_time_fly(duration_s=1.0)
    # Settle time is over
    assert hw.hsm_heater.settled
    assert not hw.hsm_heater.timeout
    eca.assert_no_errors("Temperature is in range")

    hw.mpi.sim_set_voltage(carbon=True, value=39.0)

    hw.let_time_fly(duration_s=2.0)
    assert hw.hsm_heater.settled
    assert not hw.hsm_heater.timeout
    eca.assert_errors("Temperature out of range")

    hw.mpi.sim_set_voltage(carbon=True, value=42.0)

    hw.let_time_fly(duration_s=10.0)
    eca.assert_no_errors("Temperature in range")

    #
    # Start controller - Timeouttime Test
    #
    hw.mpi.sim_set_voltage(carbon=True, value=39.0)
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.MANUAL)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual)
    hw.let_time_fly(duration_s=2.0)
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)
    eca = hw.error_counter_assertion
    assert not hw.hsm_heater.settled
    assert not hw.hsm_heater.timeout
    hw.let_time_fly(duration_s=95.0)
    error_counter_new1 = hw.get_quantity(Quantity.StatusReadErrorCounter)
    eca.assert_errors("Temperature out of range")
    assert not hw.hsm_heater.settled
    assert not hw.hsm_heater.timeout
    hw.let_time_fly(duration_s=10.0)
    assert not hw.hsm_heater.settled
    assert hw.hsm_heater.timeout
    eca.assert_errors("Temperature out of range")


if __name__ == "__main__":
    test_settletime(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
