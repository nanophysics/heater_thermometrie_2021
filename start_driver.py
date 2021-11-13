import logging

import heater_thread
import heater_hsm
from heater_driver_utils import EnumHeating, Quantity, EnumThermometrie

logger = logging.getLogger("LabberDriver")


def run_driver():
    logging.basicConfig()
    logger.setLevel(logging.INFO)

    ht = heater_thread.HeaterThread(hwserial="")
    ht._hw.sleep(1.5)
    ht.signal(heater_hsm.SignalDefrostSwitchChanged(defrost_on=False))
    ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermoff)
    ht._hw.set_quantity(Quantity.ControlWriteThermometrie, EnumThermometrie.ON)
    ht._hw.set_quantity(Quantity.ControlWriteHeating, EnumHeating.OFF)
    ht._hw.set_quantity(Quantity.ControlWritePower100, 50)
    # ht._hw.sleep(5.0)
    # ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingoff)

    ht.set_quantity(Quantity.ControlWriteHeating, EnumHeating.MANUAL)
    # ht._hw.sleep(5.0)
    # ht.expect_state(heater_hsm.HeaterHsm.state_connected_thermon_heatingmanual)

    logger.info("run()")
    ht.run()
    ht.stop()


if __name__ == "__main__":
    run_driver()
