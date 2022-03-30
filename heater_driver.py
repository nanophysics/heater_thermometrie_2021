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
