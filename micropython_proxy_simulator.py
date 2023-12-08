import logging

import config_all
from src_micropython.micropython_portable import ThermometriePT1000

logger = logging.getLogger("LabberDriver")


class Display:
    def show_lines(self, lines):
        if 1 == 0:
            for line in lines:
                print(f"   | {line:16} |")
        return b"None"


class TemperatureInsert:
    def __init__(self):
        self._resistance_OHM = {True: 0.0, False: 0.0}
        self.time_last_s = 0.0
        self._resistance_mocked = False

    def enable_thermometrie(self, enable):
        return b"None"

    def read_resistance_OHM(self, carbon):
        return f"{self._resistance_OHM[True]}".encode("ascii")

    def sim_set_resistance_OHM(self, carbon: bool, temperature_K: float):
        self._resistance_mocked = True
        self._resistance_OHM[carbon] = ThermometriePT1000.resistance_OHM(temperature_K=temperature_K)

    def sim_update_time(self, time_now_s: float, power: int):
        assert isinstance(time_now_s, float)
        assert isinstance(power, int)
        if self._resistance_mocked:
            # The voltage is mocked to a fix value
            # and should not be simulated
            return
        time_diff_s = time_now_s - self.time_last_s
        self.time_last_s = time_now_s
        reference_V = 3.3
        for carbon in (True, False):
            tau = 0.1 * time_diff_s
            tau = min(1.0, tau)
            self._resistance_OHM[carbon] = (1.0 - tau) * self._resistance_OHM[carbon] + tau * 0.005 * power * reference_V


class Heater:
    def __init__(self):
        self.power = 0

    def set_power(self, power: int):
        assert isinstance(power, int)
        self.power = power
        return b"None"


class OnewireBox:
    ONEWIRE_ID = config_all.ONEWIRE_ID_INSERT_UNDEFINED

    def __init__(self):
        self._onwire_id = self.ONEWIRE_ID

    def scan(self):
        return self._onwire_id.encode("ascii")

    def read_temp_C(self, ident):
        return b"43.43"


class OnewireInsert(OnewireBox):
    ONEWIRE_ID = config_all.ONEWIRE_ID_HEATER_UNDEFINED

    def sim_set_onewire_id(self, onewire_id: str):
        assert isinstance(onewire_id, str)
        self._onwire_id = onewire_id


class Proxy:
    def __init__(self):
        self.display = Display()
        self.temperature_insert = TemperatureInsert()
        self.heater = Heater()
        self.onewire_box = OnewireBox()
        self.onewire_insert = OnewireInsert()

    def get_defrost(self):
        return b"True"

    def get_pt1000_connected(self):
        return b"True"


class FeSimulator:
    def __init__(self):
        self.proxy = Proxy()

    def exec(self, cmd: str) -> None:
        pass

    def eval(self, cmd: str):
        try:
            return eval(cmd, {"proxy": self.proxy})  # pylint: disable=eval-used
        except Exception as e:
            logger.warning(f"{cmd}: {e}")
            raise

    def close(self):
        pass

    def sim_set_resistance_OHM(self, carbon: bool, temperature_K: float):
        self.proxy.temperature_insert.sim_set_resistance_OHM(carbon=carbon, temperature_K=temperature_K)

    def sim_update_time(self, time_now_s):
        self.proxy.temperature_insert.sim_update_time(time_now_s, self.proxy.heater.power)
