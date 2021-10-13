import logging

import micropython_proxy
import heater_thread
import heater_wrapper
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity, EnumThermometrie
from micropython_interface import TICK_INTERVAL_S

logger = logging.getLogger("LabberDriver")


def test_statemachine_a():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    ht = heater_thread.HeaterThread(hwserial=hwserial)
    ht.signal(heater_hsm.SignalDefrostSwitchChanged(on=False))
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon)

    ht.set_quantity(Quantity.ControlWriteThermometrie, EnumThermometrie.ON)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon)

    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.MANUAL)
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual)


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


def test_statemachine_settletime():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    hwserial = micropython_proxy.HWSERIAL_SIMULATE
    hw = heater_wrapper.HeaterWrapper(hwserial=hwserial)
    r = Runner(hw=hw)
    hw.mpi.sim_set_voltage(carbon=False, value=0.0)

    hw.signal(heater_hsm.SignalDefrostSwitchChanged(on=False))
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon)

    hw.set_quantity(Quantity.ControlWriteThermometrie, EnumThermometrie.ON)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon)

    hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.CONTROLLED)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)

    hw.set_quantity(Quantity.ControlWriteSettleTime, 20)
    hw.set_quantity(Quantity.ControlWriteTimeoutTime, 40)
    hw.set_quantity(Quantity.ControlWriteTemperatureToleranceBand, 1.0)
    hw.set_quantity(Quantity.ControlWriteTemperature, 21.0)
    hw.mpi.sim_set_voltage(carbon=False, value=1.6)

    r.run_for(duration_s=30)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)
    assert not hw.hsm_heater.settled
    assert not hw.hsm_heater.timeout 
    r.run_for(duration_s=30)
    assert hw.hsm_heater.timeout 

    r.run_for(duration_s=15)
    hw.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingcontrolled)

if __name__ == "__main__":
    test_statemachine_a()
