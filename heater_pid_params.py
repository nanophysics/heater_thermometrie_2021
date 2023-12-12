"""
below 100K calculated for measured step response
300K values approximated
"""

import numpy as np


class HeaterPidParams:
    def __init__(self, setpoint_k: float):
        T_array = np.array([1.1, 5.2, 12, 21, 35, 45, 55, 65, 70, 75, 85, 95, 300])
        # self.fT_array = T_array
        delay_array = np.array([1, 1, 1, 1, 3, 4, 6, 6, 6, 7, 8, 10, 20])
        # self.fdelay_array = delay_array
        slope_array = np.array([50, 15, 1, 0.2, 0.06, 0.03, 0.02, 0.01, 0.01, 0.01, 0.008, 0.008, 0.002])
        # self.fslope_array = slope_array
        Tn = 4.0 * delay_array
        # self.fTn = Tn
        Kp = 0.6 / slope_array / delay_array
        Ki = Kp / Tn
        factor = 0.3
        self.fKp = factor * np.interp(setpoint_k, T_array, Kp)
        self.fKi = factor * np.interp(setpoint_k, T_array, Ki)
        self.fKd = 0.0

        # self.fKp = 0.04
        # self.fKi = 0.01

        # self.fKp = 4.8
        # self.fKi = 0.12
        # self.fKd = 0.0


def main():
    print("T, delay, slope, Tn, Kp, Ki")
    params = HeaterPidParams(setpoint_k=5.2)
    for j in range(5):
        #        print(params.fT_array[j], params.fdelay_array[j],params.fslope_array[j],params.fTn[j],params.fKp[j],params.fKi[j])
        print(
            params.fT_array[j],
            params.fdelay_array[j],
            params.fslope_array[j],
            params.fTn[j],
            params.fKp,
            params.fKi,
        )


if __name__ == "__main__":
    main()
