# pylint: disable=import-error
# pylint: disable=consider-using-f-string

from micropython_portable import ThermometriePT1000


class DefrostProcess:
    def __init__(self, proxy):
        self._proxy = proxy
        self._pc_communication_counter = 0
        self._clear = self._proxy.display.clear
        self._show = self._proxy.display.show
        self._zeile = self._proxy.display.zeile
        self._temperature_insert = self._proxy.temperature_insert

    def pc_command(self):
        self._pc_communication_counter = -5

    @property
    def _rotator_text(self):
        return r"\|/-"[self._pc_communication_counter % 4]

    def tick(self):
        self._pc_communication_counter += 1
        if self._pc_communication_counter < 0:
            # The pc controls us and the standalone defrost logic should be off.
            return
        self._clear()
        self._control_defrost()
        self._show()

    def _control_defrost(self):
        """
        100% heizen solange PT1000 R < 1116 Ohm # "PT1000 30C"
        """
        self._proxy.heater.set_power_off()

        resistance_OHM = self._temperature_insert.read_resistance_OHM(carbon=False)
        temperature_C = resistance_OHM * ThermometriePT1000.temperature_C(resistance_OHM)
        # self._zeile(0, " {:>11.1f}C {}".format(temperature_C, self._rotator_text))
        # self._zeile(0, " {} {:>11.1f}C".format(self._rotator_text, temperature_C))
        self._zeile(0, " {:>13.1f}C".format(temperature_C))
        # self._zeile(4, " {:>14s}".format(self._rotator_text))

        if not self._proxy.get_defrost():
            self._zeile(2, " waiting for")
            self._zeile(3, " labber")
            self._zeile(4, " driver...")
            return

        self._temperature_insert.enable_thermometrie(enable=True)
        self._zeile(1, " DEFROST")
        if temperature_C < 30.0:
            self._proxy.heater.set_power_max()
            self._zeile(3, " Defrosting")
            self._zeile(4, " do not open!")
            return

        self._zeile(3, " Ready to remove")
        self._zeile(4, " vessel")
