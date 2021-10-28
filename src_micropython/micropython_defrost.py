# pylint: disable=import-error
# pylint: disable=consider-using-f-string

from micropython_portable import ThermometriePT1000


class DefrostProcess:
    def __init__(self, proxy):
        self._proxy = proxy
        self._display = proxy.display
        self._pc_communication_counter = 0
        self._temperature_insert = self._proxy.temperature_insert

    def pc_command(self):
        "Will be called at every communication with the pc (eg. labber driver)"
        self._pc_communication_counter = -5

    @property
    def _rotator_text(self):
        return r"\|/-"[self._pc_communication_counter % 4]

    def tick(self):
        self._pc_communication_counter += 1
        if self._pc_communication_counter < 0:
            # The pc controls us and the standalone defrost logic should be off.
            return
        lines = self._control_defrost()
        self._display.show_lines(lines=lines)

    def _control_defrost(self):
        """
        100% heizen solange PT1000 R < 1116 Ohm # "PT1000 30C"
        """
        self._proxy.heater.set_power_off()

        resistance_OHM = self._temperature_insert.read_resistance_OHM(carbon=False)
        temperature_C = ThermometriePT1000.temperature_C(resistance_OHM)
        # self._line(0, " {:>11.1f}C {}".format(temperature_C, self._rotator_text))
        # self._line(0, " {} {:>11.1f}C".format(self._rotator_text, temperature_C))
        lines = self._display.lines_factory()
        if 1 == 0:
            if self._pc_communication_counter % 15 < 10:
                temperature_C = -100.0
            if self._pc_communication_counter % 15 < 5:
                temperature_C = 40.0
        if temperature_C < -40.0:
            lines[0] = "          <-40C"
        else:
            lines[0] = "{:>14.0f}C".format(temperature_C)
            # lines[4] = " {:>14s}".format(self._rotator_text))

        if not self._proxy.get_defrost():
            lines[2] = " waiting for"
            lines[3] = " labber"
            lines[4] = " driver..."
            return lines

        self._temperature_insert.enable_thermometrie(enable=True)
        lines[1] = " DEFROST"
        if temperature_C < 30.0:
            self._proxy.heater.set_power_max()
            lines[3] = " Defrosting"
            lines[4] = " do not open!"
            return lines

        lines[3] = " Ready to remove"
        lines[4] = " vessel"
        return lines
