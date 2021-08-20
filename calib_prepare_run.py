import itertools
from src_micropython import micropython_portable
import calib_prepare_lib

if __name__ == '__main__':
    calib_prepare_lib.prepare_by_serial(serial='20200918_76')

    if False:
        filename = 'Drivers/compact_2012/calib_raw_dac0_2019-06-09a.txt'
        r = micropython_portable.CalibRawFileReader(filename)
        list_step_a_V, list_step_b_V = r.values()
        for iDac, step_a_V, step_b_V in zip(itertools.count(r.iDacStart), list_step_a_V, list_step_b_V):
            print('0x{:06X} {:12.9f} {:12.9f}'.format(iDac, step_a_V, step_b_V))
