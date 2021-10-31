import pytest

import micropython_proxy
import heater_wrapper
from src_micropython.micropython_portable import Thermometrie

import config_all


@pytest.mark.simulate
@pytest.mark.parametrize("insert", config_all.dict_insert.values())
def test_calibration(insert):
    hw = heater_wrapper.HeaterWrapper(hwserial=micropython_proxy.HWSERIAL_SIMULATE)
    hw.insert_connected(onewire_id=insert.ONEWIRE_ID)

    calibration = hw.insert_calibration.Calibration(carbon_OHM=10.0, pt1000_OHM=1000.0)
    assert isinstance(calibration.carbon_K, float)
    assert isinstance(calibration.pt1000_K, float)
    assert isinstance(calibration.calibrated_K, float)
    assert Thermometrie.ZEROCELSIUS_K - 1.0 <= calibration.pt1000_K <= Thermometrie.ZEROCELSIUS_K + 1.0
    assert Thermometrie.ZEROCELSIUS_K - 1.0 <= calibration.calibrated_K <= Thermometrie.ZEROCELSIUS_K + 1.0
