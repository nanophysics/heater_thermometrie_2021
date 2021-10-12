class FeSimulator:
    def __init__(self):
        self.voltage_carbon = {True: -1.0, False: -1.0}

    def exec(self, cmd: str) -> None:
        pass

    def eval(self, cmd: str):  # pylint: disable=too-many-return-statements
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
        self.voltage_carbon[carbon] = value
