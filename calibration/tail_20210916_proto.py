import math


def transition(carbon_K: float, pt1000_K: float, transition_K=30.0):
    """
    https://kitchingroup.cheme.cmu.edu/blog/2013/01/31/Smooth-transitions-between-discontinuous-functions/
    """
    alpha_K = 2.0  # 2.0 : changes over about +- 10K, do not change
    sigma = 1.0 / (1 + math.exp(-(pt1000_K - transition_K) / alpha_K))
    calibrated_K = (1 - sigma) * carbon_K + sigma * pt1000_K
    return calibrated_K


class Calibration:
    PT1000_30C_OHM = 1116.73
    ZEROCELSIUS_K = 273.15

    def __init__(self, carbon_OHM: float, pt1000_OHM: float) -> None:
        self.carbon_OHM = carbon_OHM
        self.pt1000_OHM = pt1000_OHM
        # The following line corresponds to
        # micropython_portable.py::ThermometriePT1000.temperature_C()
        self.carbon_K = self.ZEROCELSIUS_K + (pt1000_OHM - 1000.0) * 30.0 / (self.PT1000_30C_OHM - 1000.0)
        self.pt1000_K = self.carbon_K
        self.calibrated_K = transition(carbon_K=self.carbon_K, pt1000_K=self.pt1000_K, transition_K=30.0)


def main():
    print("real_K, carbon_K, pt1000_K, calibrated_K, calibrated_K-real_K")
    for real_K in range(300):
        carbon_K = real_K - 1.0
        pt1000_K = real_K + 1.0
        calibrated_K = transition(carbon_K, pt1000_K)
        print(f"{real_K:0.3f}, {carbon_K:0.3f}, {pt1000_K:0.3f}, {calibrated_K:0.3f}, {calibrated_K-real_K:0.3f}")


if __name__ == "__main__":
    main()
