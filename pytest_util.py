import pytest
import micropython_proxy

TEST_HW_SIMULATE = [
    pytest.param(""),
    pytest.param(micropython_proxy.HWSERIAL_SIMULATE, marks=pytest.mark.simulate),
]
