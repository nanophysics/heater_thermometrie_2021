
from src_micropython . micropython_portable import ThermometriePT1000

def test_pt1000_kennlinie():
    assert  ThermometriePT1000.temperature_C(resistance_OHM=1000.0) == 0.0
    assert  ThermometriePT1000.temperature_C(resistance_OHM=ThermometriePT1000.PT1000_30C_OHM) == 30.0
