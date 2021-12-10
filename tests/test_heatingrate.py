import pathlib

import pytest

from heater_heatingrate import HeatingRate

THIS_FILE = pathlib.Path(__file__).resolve()

TEST_HEATING_POWER_MAX_W = 3.3


def test_heatingrate_values():
    hr = HeatingRate(heating_power_max_W=TEST_HEATING_POWER_MAX_W)
    print(hr.get_ADC(power_W=1.0))

    assert hr.get_ADC(power_W=3.0) == 50058
    assert hr.get_ADC(power_W=-1.0) == HeatingRate.ADC_MIN
    assert hr.get_ADC(power_W=1000.0) == HeatingRate.ADC_MAX


def test_heatingrate_plot():
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        pytest.skip("import failed: 'pip install matplotlib'")

    hr = HeatingRate(heating_power_max_W=TEST_HEATING_POWER_MAX_W)
    array_power_W = [0.001 * i for i in range(0, 6000)]
    array_adc_1 = [hr.get_ADC(p_W) for p_W in array_power_W]

    _fig, ax = plt.subplots()
    ax.plot(array_power_W, array_adc_1)

    ax.set(xlabel="power (W)", ylabel="code 16 bit DAC ", title="Code at power")
    ax.grid()

    # plt.show()
    filename = THIS_FILE.with_stem(f"{THIS_FILE.stem}_testresult").with_suffix(".png")
    plt.savefig(filename, dpi=None)
