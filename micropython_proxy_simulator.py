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
        self.voltage_carbon = {True: 0.0, False: 0.0}

    def enable_thermometrie(self, enable):
        return b"None"

    def get_voltage(self, carbon):
        return f"{self.voltage_carbon[True]}".encode("ascii")

    def sim_set_voltage(self, carbon: bool, value: float):
        self.voltage_carbon[carbon] = value


class Heater:
    def set_power(self, power):
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

    def eval(self, cmd: str):  # pylint: disable=too-many-return-statements
        try:
            return eval(cmd, {"proxy": self.proxy})
        except Exception as e:
            logger.warning(f"{cmd}: {e}")
            raise

        if cmd.startswith("proxy.display."):
            return b"None"
        if cmd == "proxy.onewire_box.scan()":
            return b"28E3212E0D00002E"
        if cmd == "proxy.onewire_box.read_temp('28E3212E0D00002E')":
            return b"42.42"
        if cmd.startswith("proxy.onewire_insert.set_power("):
            return b"None"
        if cmd == "proxy.onewire_insert.scan()":
            return b"28d821950d00003e"
        if cmd == "proxy.onewire_insert.read_temp('28d821950d00003e')":
            return b"43.43"
        if cmd == "proxy.get_defrost()":
            return b"True"
        if cmd.startswith("proxy.temperature_insert.enable_thermometrie(enable="):
            return b"None"
        if cmd.startswith("proxy.temperature_insert.get_voltage(carbon="):
            return f"{self.voltage_carbon[True]}".encode("ascii")
        if cmd.startswith("proxy.heater.set_power(power="):
            return b"None"
        raise NotImplementedError()

    def close(self):
        pass

    def sim_set_voltage(self, carbon: bool, value: float):
        self.proxy.temperature_insert.sim_set_voltage(carbon, value)
