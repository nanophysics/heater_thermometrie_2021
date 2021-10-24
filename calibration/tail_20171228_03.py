class Calibration:
    PTC30K_OHM = 1116.73
    ZEROCELSIUS_K = 273.15

    def __init__(self, carbon_OHM: float, pt1000_OHM: float) -> None:
        self.carbon_OHM = carbon_OHM
        self.pt1000_OHM = pt1000_OHM
        # The following line corresponds to
        # micropython_portable.py::ThermometriePT1000.temperature_C()
        self.carbon_K = self.ZEROCELSIUS_K + (pt1000_OHM - 1000.0) * 30.0 / (self.PTC30K_OHM - 1000.0)
        self.pt1000_K = self.carbon_K
        self.calibrated_K = self.carbon_K
