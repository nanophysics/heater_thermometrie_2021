import logging

logger = logging.getLogger("LabberDriver")


class Display:
    ZEILEN = 5

    def __init__(self):
        self.zeilen = ["" for zeile in range(self.ZEILEN)]

    def zeile(self, i, text):
        self.zeilen[i] = text
        return b"None"

    def clear(self):
        self.zeilen = ["" for zeile in range(self.ZEILEN)]
        return b"None"

    def show(self):
        for zeile in self.zeilen:
            print(f"   | {zeile:16} |")
        return b"None"


class TemperatureInsert:
    def __init__(self):
        self.voltage_carbon_V = {True: 0.0, False: 0.0}
        self.time_last_s = 0.0
        self._voltage_mocked = False

    def enable_thermometrie(self, enable):
        return b"None"

    def get_voltage(self, carbon):
        return f"{self.voltage_carbon_V[True]}".encode("ascii")

    def sim_set_voltage(self, carbon: bool, value: float):
        self._voltage_mocked = True
        self.voltage_carbon_V[carbon] = value

    def sim_update_time(self, time_now_s: float, power: int):
        assert isinstance(time_now_s, float)
        assert isinstance(power, int)
        if self._voltage_mocked:
            # The voltage is mocked to a fix value
            # and should not be simulated
            return
        time_diff_s = time_now_s - self.time_last_s
        self.time_last_s = time_now_s
        reference_V = 3.3
        for carbon in (True, False):
            tau = 0.1 * time_diff_s
            tau = min(1.0, tau)
            self.voltage_carbon_V[carbon] = (1.0 - tau) * self.voltage_carbon_V[carbon] + tau * 0.005 * power * reference_V


class Heater:
    def __init__(self):
        self.power = 0.0

    def set_power(self, power: int):
        assert isinstance(power, int)
        self.power = power
        return b"None"


class OnewireBox:
    def scan(self):
        return b"28d821950d00003e"

    def read_temp(self, ident):
        return b"43.43"


class OnewireInsert(OnewireBox):
    def set_power(self, on):
        return b"None"


class Proxy:
    def __init__(self):
        self.display = Display()
        self.temperature_insert = TemperatureInsert()
        self.heater = Heater()
        self.onewire_box = OnewireBox()
        self.onewire_insert = OnewireInsert()

    def get_defrost(self):
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

    def sim_set_voltage(self, carbon: bool, value: float):
        self.proxy.temperature_insert.sim_set_voltage(carbon, value)

    def sim_update_time(self, time_now_s):
        self.proxy.temperature_insert.sim_update_time(time_now_s, self.proxy.heater.power)
