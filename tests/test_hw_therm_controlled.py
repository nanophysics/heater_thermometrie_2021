import logging

import pytest

from pytest_util import TEST_HW_SIMULATE
import micropython_proxy
import heater_wrapper
import heater_hsm
from test_constants import *
from heater_driver_utils import EnumHeating, Quantity

logger = logging.getLogger("LabberDriver")


class Runner:
    def __init__(self, hwserial):
        logging.basicConfig()
        logger.setLevel(logging.DEBUG)

        self._hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)
        self._eca = self._hw.error_counter_assertion

    def set_quantity(self, quantity, value):
        self._hw.set_quantity(quantity, value)

    def expect_state(self, meth):
        return self._hw.expect_state(meth)

    def let_time_fly(self, duration_s):
        self._hw.let_time_fly(duration_s=duration_s)

    def reset_errors(self):
        self._eca.reset()

    def assert_no_errors(self):
        self._eca.assert_no_errors()

    def assert_errors(self):
        self._eca.assert_errors()

    def init_40K(self):
        # Prepare Settle Test
        self.set_quantity(Quantity.ControlWriteTemperature, TEMPERATURE_SET40_K)
        self.set_quantity(Quantity.ControlWriteTemperatureToleranceBand, 1.0)
        self.set_quantity(Quantity.ControlWriteSettleTime, SETTLE_TIME_S)
        self.set_quantity(Quantity.ControlWriteTimeoutTime, TIMEOUT_TIME_S)
        self._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=40.5)

    def start_40K_35K(self):
        #
        # Start controller - Settle Time Test
        #
        self._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=TEMPERATURE_OUTSIDE_K)
        self.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
        self._hw.expect_display(
            """
        |           16.1K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  out of range    |
        |  errors 0        |
"""
        )
        assert not self._hw.hsm_heater.is_settled()

        # Wait with temperature outside range
        self.let_time_fly(duration_s=20.0)
        assert not self._hw.hsm_heater.is_settled()
        self.assert_errors()

    def continue_40K_40K_A(self):
        # Temperature inside range: Settle time starts
        self._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=TEMPERATURE_SET40_K)

        self.let_time_fly(duration_s=SETTLE_TIME_S - 1.0)
        # Settle time is NOT over
        assert not self._hw.hsm_heater.is_settled()

        self.assert_no_errors()
        self.let_time_fly(duration_s=1.0)
        # Settle time is over
        assert self._hw.hsm_heater.is_settled()

        self._hw.expect_display(
            """
        |           40.0K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  in range 10s    |
        |  errors 20       |
        """
        )

    def continue_40K_35K(self):
        self._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=TEMPERATURE_OUTSIDE_K)

        self.let_time_fly(duration_s=2.0)
        assert self._hw.hsm_heater.is_outofrange()

        self.assert_errors()

    def continue_40K_40K_B(self):
        self._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=TEMPERATURE_SET40_K)

        self.let_time_fly(duration_s=10.0)
        self.assert_no_errors()

    def manual_then_controlled_40K_35K_timeout(self):
        #
        # Start controller - Timeouttime Test
        #
        self._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=TEMPERATURE_OUTSIDE_K)
        self.set_quantity(Quantity.ControlWriteHeating, EnumHeating.MANUAL)
        self.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual)
        self.let_time_fly(duration_s=2.0)
        self.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
        self.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)
        self._eca.reset()
        assert not self._hw.hsm_heater.is_settled()

        self.let_time_fly(duration_s=95.0)
        self._hw.get_quantity(Quantity.StatusReadErrorCounter)
        self.assert_errors()
        assert not self._hw.hsm_heater.is_settled()

        self.let_time_fly(duration_s=10.0)
        assert not self._hw.hsm_heater.is_settled()
        self.assert_errors()

    def start_40K_40K(self):
        self._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=40.0)
        self.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
        self.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)
        self.reset_errors()

        assert not self._hw.hsm_heater.is_settled()

        # Wait with temperature outside range
        self.let_time_fly(duration_s=SETTLE_TIME_S + 2.0)
        assert self._hw.hsm_heater.is_settled()

        self.assert_no_errors()

    def write_and_wait_40K_40K_C(self):
        # If the temperature is already set, there will be no settle time
        self.set_quantity(Quantity.ControlWriteTemperatureAndSettle, TEMPERATURE_SET40_K)
        self.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)
        self.let_time_fly(duration_s=2.0)
        assert self._hw.hsm_heater.is_settled()

    def change_42K_42K_C(self):
        # If the temperature is already set, there will be no settle time
        self._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=TEMPERATURE_SET42_K)
        self.set_quantity(Quantity.ControlWriteTemperature, TEMPERATURE_SET42_K)
        self.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)
        assert self._hw.hsm_heater.is_settled()

        self.let_time_fly(duration_s=2.0)
        self._hw.expect_display(
            """
        |           42.0K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  in range 16s    |
        |  errors 0        |
        """
        )
        assert self._hw.hsm_heater.is_settled()

    def change_40K_35K_C(self):
        # If the temperature is already set, there will be no settle time
        self._hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=TEMPERATURE_OUTSIDE_K)
        self.set_quantity(Quantity.ControlWriteTemperature, TEMPERATURE_SET40_K)
        self.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)
        self.let_time_fly(duration_s=TIMEOUT_TIME_S - 1.0)
        self._hw.expect_display(
            """
        |           35.0K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  out of range    |
        |  errors 59       |
        """
        )


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_settletime(hwserial):
    r = Runner(hwserial=hwserial)

    r.init_40K()
    r.start_40K_35K()
    r.continue_40K_40K_A()
    r.continue_40K_35K()
    r.manual_then_controlled_40K_35K_timeout()
    r.continue_40K_40K_B()


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_settletime_repetitive(hwserial):
    """
    Verify behaviour of
      ControlWriteTemperatureAndSettle = "temperature and settle"

    When calling the first time, the settle time should apply (the tail should settle is temperature).
    When calling consecutive times, no settle time is required (as the controller hold the temperature constant)
    A settle time applays again if:
      - The "temperature and settle" changed.
      - The heater mode was changed (eg. manual)
    """
    r = Runner(hwserial=hwserial)

    r.init_40K()
    r.start_40K_40K()
    r.write_and_wait_40K_40K_C()
    r.change_42K_42K_C()
    r.change_40K_35K_C()


# New test
# set by combobox controlled
#   controlled
#   off
# set by temp_settle
# set by change temp_settle


# combine tests
#   set_combobox_controlled
#   set_temp_settle_same
#   set_temp_settle_diff


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_settletime_not_reset_by_manual(hwserial):
    """
    If heating is manual or off, we still measure the temperature.
    Therefore the settle time is still calculated.
    """
    r = Runner(hwserial=hwserial)
    hw = r._hw

    r.init_40K()
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.let_time_fly(duration_s=TIMEOUT_TIME_S + 2.0)
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.MANUAL)
    hw.let_time_fly(duration_s=2.0)
    hw.expect_display(
        """
        |           40.5K  |
        |  HEATING         |
        |  MANUAL          |
        |  in range 64s    |
        |  errors 0        |
    """
    )
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.OFF)
    hw.let_time_fly(duration_s=2.0)
    hw.expect_display(
        """
        |           40.5K  |
        |  HEATING         |
        |  OFF             |
        |  in range 66s    |
        |  errors 0        |
    """
    )
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.expect_display(
        """
        |           40.5K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  in range 66s    |
        |  errors 0        |
    """
    )
    hw.let_time_fly(duration_s=2.0)
    hw.expect_display(
        """
        |           40.5K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  in range 68s    |
        |  errors 0        |
    """
    )


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_settletime_reset_by_off(hwserial):
    """
    If heating is off, we do not measure the temperature.
    Therefore the settle time has to be reset.
    """
    r = Runner(hwserial=hwserial)
    hw = r._hw

    r.init_40K()
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.let_time_fly(duration_s=TIMEOUT_TIME_S + 2.0)
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.OFF)
    hw.let_time_fly(duration_s=2.0)
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.let_time_fly(duration_s=2.0)
    hw.expect_display(
        """
        |           40.5K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  in range 66s    |
        |  errors 0        |
    """
    )


@pytest.mark.parametrize("hwserial", TEST_HW_SIMULATE)
def test_controlled_off_controlled(hwserial):
    """
    Combobox heating controlled -> off -> controlled
    Verify that timeout time starts from 0
    """
    r = Runner(hwserial=hwserial)
    hw = r._hw

    r.init_40K()
    hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=40.5)
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.let_time_fly(duration_s=TIMEOUT_TIME_S + 2.0)
    hw.expect_display(
        """
        |           40.5K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  in range 62s    |
        |  errors 0        |
    """
    )
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.OFF)
    hw.let_time_fly(duration_s=TIMEOUT_TIME_S + 2.0)
    hw.expect_display(
        """
        |           40.5K  |
        |  HEATING         |
        |  OFF             |
        |  in range 124s   |
        |  errors 0        |
    """
    )
    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.mpi.sim_set_resistance_OHM(carbon=True, temperature_K=TEMPERATURE_SET42_K)
    hw.let_time_fly(duration_s=TIMEOUT_TIME_S + 2.0)
    hw.expect_display(
        """
        |           42.0K  |
        |  HEATING         |
        |  CONTROLLED      |
        |  out of range    |
        |  errors 62       |
    """
    )


if __name__ == "__main__":
    # test_settletime(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
    # test_settletime_repetitive(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
    test_controlled_off_controlled(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
    test_settletime_not_reset_by_manual(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
