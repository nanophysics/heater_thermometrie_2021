"""
The parameters below are optimized for 30 C.

TODO: Change the parameters based on setpoint_k.
"""


class HeaterPidParams:
    def __init__(self, setpoint_k: float):
        self.fKp = 4.8
        self.fKi = 0.12
        self.fKd = 0.0
