# Example Heating Power
# Measurement on prototype insert_2019

import numpy

def find_code(power_set_W):
    # The heater_thermometrie_2021 has a special characteristics. Very fine resolution at low heating power.
    # The measured values here are measured by Peter with the heater_thermometrie_2021 prototype and insert_2019 prototype.
    left = 0 # minimal dac code
    right = 2**16-1 # maximal dac code
    power_W = [0.00E0, 6.15E-13, 7.59E-13, 8.28E-13, 7.89E-13, 5.68E-13, 1.26E-12, 5.77E-13, 9.35E-13, 1.49E-12, 2.16E-12, 2.09E-12, 2.81E-12, 2.65E-12, 3.21E-12, 3.51E-12, 4.67E-12, 5.79E-12, 7.23E-12, 9.19E-12, 1.23E-11, 1.41E-11, 1.91E-11, 2.75E-11, 3.50E-11, 4.77E-11, 6.25E-11, 9.72E-11, 1.30E-10, 1.91E-10, 2.96E-10, 4.57E-10, 7.25E-10, 1.17E-9, 2.02E-9, 3.71E-9, 7.38E-9, 1.54E-8, 3.49E-8, 8.53E-8, 2.20E-7, 6.09E-7, 1.77E-6, 5.01E-6, 1.33E-5, 3.28E-5, 7.28E-5, 1.45E-4, 2.66E-4, 4.55E-4, 6.14E-4, 1.19E-3, 1.82E-3, 2.68E-3, 3.88E-3, 5.52E-3, 7.73E-3, 1.07E-2, 1.46E-2, 1.97E-2, 2.63E-2, 3.51E-2, 4.64E-2, 6.08E-2, 7.94E-2, 1.03E-1, 1.34E-1, 1.73E-1, 2.24E-1, 2.88E-1, 3.70E-1, 4.74E-1, 6.06E-1, 7.73E-1, 9.84E-1, 1.25E0, 1.59E0, 2.02E0, 2.56E0, 3.24E0, 4.11E0, 5.08E0]
    dac_code = [0, 7, 7, 8, 9, 10, 12, 13, 15, 16, 18, 21, 23, 26, 29, 33, 37, 41, 46, 52, 58, 66, 74, 83, 93, 104, 117, 131, 147, 165, 185, 207, 233, 261, 293, 328, 369, 413, 464, 521, 584, 655, 735, 825, 926, 1039, 1165, 1308, 1467, 1646, 1847, 2072, 2325, 2609, 2927, 3285, 3685, 4135, 4640, 5206, 5841, 6554, 7353, 8250, 9257, 10387, 11654, 13076, 14671, 16462, 18470, 20724, 23253, 26090, 29273, 32845, 36853, 41350, 46395, 52056, 58408, 65535]
    max_power_W = 3.3 # todo: implement somehow. max power for powersupply 0.22 A, might change later if not enough
    assert len(power_W) == len(dac_code)
    return numpy.interp(power_set_W, power_W, dac_code).astype(int)

print(find_code(power_set_W=1.0))

assert find_code(power_set_W=-1.0) == 0
assert find_code(power_set_W=1000.0) <= 2**16-1 # maximal dac code

import matplotlib.pyplot as plt

power_array = numpy.arange(0.0, 6.0, 0.001)
code_array = find_code(power_array)

fig, ax = plt.subplots()
ax.plot(power_array, code_array)

ax.set(xlabel='power (W)', ylabel='code 16 bit DAC ',
       title='Code at power')
ax.grid()

plt.show()
