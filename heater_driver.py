# pylint: disable=dangerous-default-value
import pathlib
import logging

import InstrumentDriver  # pylint: disable=import-error

import micropython_proxy
import heater_thread
from heater_wrapper import DIRECTORY_OF_THIS_FILE, QuantityNotFoundException

logger = logging.getLogger("LabberDriver")
LABBER_INTERNAL_QUANTITIES = ("Expert",)
MODEL_SIMULATION = "Simulation"


class Driver(InstrumentDriver.InstrumentWorker):
    """This class implements the Compact 2012 driver"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ht = None

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

        # open connection
        hwserial = self.comCfg.address
        if self.getModel() == MODEL_SIMULATION:
            hwserial = micropython_proxy.HWSERIAL_SIMULATE
        self.ht = heater_thread.HeaterThread(hwserial=hwserial)

        # Reset the usb connection (it must not change the applied voltages)
        self.log(
            f"ETH Heater Thermometrie 2021: Connection resetted at startup. hwserial={hwserial} model={self.getModel()}"
        )

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.ht.stop()

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of multiple calls, to set multiple voltages efficiently
        if quant.name in LABBER_INTERNAL_QUANTITIES:
            return value
        try:
            value_new = self.ht.set_value(name=quant.name, value=value)
            logger.debug(f"performSetValue('{quant.name}', '{value}') -> '{value_new}'")
            return value_new
        except QuantityNotFoundException as e:
            logger.exception(e)
            raise

    def checkIfSweeping(self, quant):
        """Always return false, sweeping is done in loop"""
        return False

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # only implmeneted for geophone voltage
        logger.debug(f"performGetValue({quant.name})")
        if quant.name in LABBER_INTERNAL_QUANTITIES:
            return quant.getValue()
        try:
            value = self.ht.get_value(name=quant.name)
            logger.debug(f"performGetValue({quant.name}) -> '{value}'")
            return value
        except QuantityNotFoundException as e:
            logger.exception(e)
            raise
