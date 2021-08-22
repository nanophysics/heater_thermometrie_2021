import io
import os

try:
    import numpy as np
    import matplotlib.pyplot as plt
except ImportError as e:
    print(e)

import src_micropython.micropython_portable as micropython_portable

DIRECTORY_CALIBRATION_RAW = "calibration_raw"
DIRECTORY_CALIBRATION_RAW_FULL = os.path.join(os.path.dirname(__file__), DIRECTORY_CALIBRATION_RAW)
DIRECTORY_CALIBRATION_CORRECTION = "calibration_correction"
DIRECTORY_CALIBRATION_CORRECTION_FULL = os.path.join(os.path.dirname(__file__), DIRECTORY_CALIBRATION_CORRECTION)


def get_directory_calibration_correction_full_by_serial(serial):
    directory_full = os.path.join(DIRECTORY_CALIBRATION_CORRECTION_FULL, serial)
    if not os.path.exists(directory_full):
        os.makedirs(directory_full)
    return directory_full


FILENAME_CALIBRATION_CORRECTION_NPZ = "calibration_correction.npz"
FILENAME_CALIBRATION_CORRECTION_TXT = "calibration_correction.txt"
FILENAME_CALIB_RAW_TEMPLATE = "calib_raw_{}_dac{}-{:02d}.txt"
FILENAME_CALIB_RAW_TEMPLATE_DAC12 = "calib_raw_{}_gain_DAC12.txt"

CALIB_FILES_PER_DAC = 32

#
# Logic Peter to calculate 'calib_correction'.
#

F_TOLERANCE_GAIN = 0.2


def highpassfilter(inputarray, cutoff_frequency=0.00001):
    # Highpassfilter https://tomroelandts.com/articles/how-to-create-a-simple-high-pass-filter
    # https://fiiir.com/
    N = 10001  # Filter length, must be odd. At least about  2 / cutoff_frequency.
    print("calculaing highpassfilter, filter taps {:d}, can take a while".format(N))
    h = np.sinc(2 * cutoff_frequency * (np.arange(N) - (N - 1) / 2))  # Compute sinc filter.
    h *= np.blackman(N)  # Apply window.
    h /= np.sum(h)  # Normalize to get unity gain.
    h = -h  # Create a high-pass filter from the low-pass filter through spectral inversion.
    h[(N - 1) // 2] += 1
    inputarray_paded = np.pad(inputarray, (N, N), "edge")  # padding to reduce effects on the edge
    inputarray_paded_filtered = np.convolve(inputarray_paded, h, mode="same")
    inputarray_filtered = inputarray_paded_filtered[N:-N]  # remove padding
    return inputarray_filtered


def find_solution(stepsize_V, f_dac_12_int_per_V):
    stepsize_dac_12 = stepsize_V * f_dac_12_int_per_V  # steps of dac_20 in units of dac_12
    median_step_size_int = np.median(stepsize_dac_12)
    dac_12_limit_h_dac_12 = 2 ** compact_2012_dac.dac_12_bit - median_step_size_int
    stepsize_deviation_dac_12 = stepsize_dac_12 - np.median(stepsize_dac_12)  # we only have to correct for the offset from the theoretical step value
    stepsum_dac_12 = np.cumsum(stepsize_deviation_dac_12)  # the correction value used for dac_12 is the sum of the deviation of the steps
    # np.save('stepsum_dac_12.npy', stepsum_dac_12)
    # assert(False)
    solution_found = False
    cutoff_frequency_found = 0.0
    # We have to highpass filter stepsum_dac_12 as we only have a limited dac_12 range and we only want to smooth. We do not correct gain, offset or linearity of the dac_20.
    # We choose the cutoff_frequency as low as possible.
    for cutoff_frequency in np.logspace(-3, -1, 10, endpoint=True):  # cutoff_frequency 0.001 seams to be a good compromise, 2020-01-04 Peter
        correction_dac_12 = np.around(-highpassfilter(stepsum_dac_12, cutoff_frequency) + dac_12_mid_dac_12).astype(int)
        correction_dac_12_cliped = np.clip(correction_dac_12, a_min=dac_12_limit_l_dac_12, a_max=dac_12_limit_h_dac_12)
        if (correction_dac_12 == correction_dac_12_cliped).all():  # ok, in usable range
            solution_found = True
            cutoff_frequency_found = cutoff_frequency
            # plt.plot(correction_dac_12)
            # plt.show()
            break
        print("No solution found with cutoff_frequency {:e}".format(cutoff_frequency))

    assert solution_found
    print("Solution found with cutoff_frequency {:e}".format(cutoff_frequency_found))
    return stepsum_dac_12, stepsize_dac_12, correction_dac_12


STEPSIZE_EXPECTED_MEAN_MIN_V = 17e-6
STEPSIZE_EXPECTED_MEAN_V = 19e-6
STEPSIZE_EXPECTED_MEAN_MAX_V = 21e-6


def get_DAC12_int_per_V(serial, iDAC_index):
    filename = FILENAME_CALIB_RAW_TEMPLATE_DAC12.format(serial)
    filenameFull = os.path.join(DIRECTORY_CALIBRATION_RAW_FULL, filename)

    i_counter = 0
    f_DAC12_sum_V = 0.0
    f_DAC12_last_V = None

    if not os.path.exists(filenameFull):
        print("{}: File missing, using fallback.".format(filenameFull))
        return compact_2012_dac.f_fallback_dac_12_int_per_V

    with open(filenameFull, "r") as fIn:
        for line in fIn.readlines():
            line = line.strip()
            _iDAC_index, _iDAC12_value, _iADC24_signed = line.split("\t")
            _iDAC_index, _iDAC12_value, _iADC24_signed = int(_iDAC_index), int(_iDAC12_value), int(_iADC24_signed)
            if _iDAC_index != iDAC_index:
                continue
            fDAC12_value = micropython_portable.convert_ADC24_signed_to_V(_iADC24_signed)
            if f_DAC12_last_V is None:
                f_DAC12_last_V = fDAC12_value
                continue
            i_counter += 1
            f_DAC12_sum_V += abs(fDAC12_value - f_DAC12_last_V)
            f_DAC12_last_V = fDAC12_value

    if i_counter < 10:
        print("{}: Only {} measurements. Using fallback.".format(filenameFull, i_counter))
        return compact_2012_dac.f_fallback_dac_12_int_per_V

    f_range_V = f_DAC12_sum_V / i_counter
    f_dac_12_int_per_V = 2 ** 12 / f_range_V

    if not ((1 - F_TOLERANCE_GAIN) * compact_2012_dac.f_fallback_dac_12_int_per_V < f_dac_12_int_per_V < (1 + F_TOLERANCE_GAIN) * compact_2012_dac.f_fallback_dac_12_int_per_V):
        raise Exception("{}: Out of range. Using fallback.".format(filenameFull))

    return f_dac_12_int_per_V


def prepare_by_serial(serial):
    """
    Reads all files for serial in 'calibration_raw'.
    Calculates and write the correction-file in directory 'calibration_raw'.
    """
    calib_correction_data = CalibCorrectionData(serial)

    for iDAC_index in range(micropython_portable.DACS_COUNT):
        f_DAC12_int_per_V = get_DAC12_int_per_V(serial, iDAC_index)
        calib_correction_data.set_f_DAC12_int_per_V(iDAC_index, f_DAC12_int_per_V)
        calib_correction_data.f_comments.write("DA{}, f_DAC12_int_per_V/f_fallback_dac_12_int_per_V={}\n".format(iDAC_index + 1, f_DAC12_int_per_V / compact_2012_dac.f_fallback_dac_12_int_per_V))
    calib_correction_data.f_comments.write("\n")

    iDacFileSize = micropython_portable.DAC20_MAX // CALIB_FILES_PER_DAC

    for iDacA_index in range(0, micropython_portable.DACS_COUNT, 2):
        # Fill default-value 19uV: Empty files will not introduce big steps.
        array_stepsize_a_V = np.full(shape=[micropython_portable.DAC20_MAX], fill_value=STEPSIZE_EXPECTED_MEAN_V, dtype=np.float)
        array_stepsize_b_V = np.full(shape=[micropython_portable.DAC20_MAX], fill_value=STEPSIZE_EXPECTED_MEAN_V, dtype=np.float)

        for iFileNum in range(CALIB_FILES_PER_DAC):
            iDacStart = iFileNum * iDacFileSize
            filename = FILENAME_CALIB_RAW_TEMPLATE.format(serial, iDacA_index, iDacStart // iDacFileSize)
            filenameFull = os.path.join(DIRECTORY_CALIBRATION_RAW_FULL, filename)
            if not os.path.exists(filenameFull):
                print("WARNING: File missing {}!".format(filename))
                input("File missing. Please only continue by hit enter if you know what you do!")
                continue

            r = micropython_portable.CalibRawFileReader(filenameFull)

            print("iDacA_index: ", iDacA_index, "   filename: ", filename)
            list_step_a_V, list_step_b_V = r.values()
            assert iDacA_index == r.iDacA_index
            assert iDacStart == r.iDacStart
            assert len(list_step_a_V) == len(list_step_b_V)
            assert iDacFileSize >= len(list_step_a_V) - 1
            assert iDacFileSize >= len(list_step_b_V) - 1

            VERSATZ = 1

            array_stepsize_a_V[iDacStart + VERSATZ : iDacStart + len(list_step_a_V) + VERSATZ] = list_step_a_V
            array_stepsize_b_V[iDacStart + VERSATZ : iDacStart + len(list_step_b_V) + VERSATZ] = list_step_b_V

            array_stepsize_a_V[0] = array_stepsize_a_V[1]
            array_stepsize_b_V[0] = array_stepsize_b_V[1]

        def find_and_add_solution_for_dac(iDac_index_, array_stepsize_V):
            f_DAC12_int_per_V = calib_correction_data.get_f_DAC12_int_per_V(iDac_index_)

            mean_V = array_stepsize_V.mean()
            assert STEPSIZE_EXPECTED_MEAN_MIN_V < mean_V < STEPSIZE_EXPECTED_MEAN_MAX_V, "Expected a step of about 19uV but got {} V. Check the cabeling!".format(mean_V)
            print("Search solution for iDac_index_", iDac_index_)
            _stepsum_dac_12, _stepsize_dac_12, correction_dac_12 = find_solution(array_stepsize_V, f_DAC12_int_per_V)

            calib_correction_data.set_correction(iDac_index=iDac_index_, data=correction_dac_12)
            calib_correction_data.print_extrema(iDac_index=iDac_index_, data=correction_dac_12)

        find_and_add_solution_for_dac(iDac_index_=iDacA_index + 0, array_stepsize_V=array_stepsize_a_V)
        find_and_add_solution_for_dac(iDac_index_=iDacA_index + 1, array_stepsize_V=array_stepsize_b_V)

    calib_correction_data.save()


#
# Classes to read and write 'calib_correction'
#
class CalibCorrectionData:
    def __init__(self, serial):
        self.serial = serial
        directory = get_directory_calibration_correction_full_by_serial(serial)
        self.filename_npz = os.path.join(directory, FILENAME_CALIBRATION_CORRECTION_NPZ)
        self.filename_txt = os.path.join(directory, FILENAME_CALIBRATION_CORRECTION_TXT)

        self.f_comments = io.StringIO()
        self.data = np.zeros(shape=[micropython_portable.DACS_COUNT, micropython_portable.DAC20_MAX], dtype=np.uint16)
        self.data_f_DAC12_int_per_V = np.zeros(shape=[micropython_portable.DACS_COUNT], dtype=np.float)

    def set_correction(self, iDac_index, data):
        """
        'data' contains the calib_correction for 'dac_index'. The first dac-value in 'data' is 'iDacStart'
        """
        assert 0 <= iDac_index < micropython_portable.DACS_COUNT
        assert len(data.shape) == 1
        assert data.shape[0] == micropython_portable.DAC20_MAX

        assert data.min() >= 0
        assert data.max() < micropython_portable.DAC12_MAX_CORRECTION_VALUE

        self.data[iDac_index : iDac_index + 1, 0 : data.shape[0]] = data

    def set_f_DAC12_int_per_V(self, iDac_index, f_DAC12_int_per_V):
        self.data_f_DAC12_int_per_V[iDac_index] = f_DAC12_int_per_V

    def get_f_DAC12_int_per_V(self, iDac_index):
        return self.data_f_DAC12_int_per_V[iDac_index]

    def print_extrema(self, iDac_index, data):
        # import numpy as np
        # R = np.array((2, 2, 4, 5, 0))
        # np.diff(R)
        # array([ 0,  2,  1, -5])
        data_diff = np.diff(data)
        argmax = np.argmax(data_diff)
        argmin = np.argmin(data_diff)

        argmin = int(argmin)
        argmax = int(argmax)

        VERSATZ = 1
        argmin += VERSATZ
        argmax += VERSATZ

        print(f"argmax={argmax}, argmin={argmin}\n")

        def print2(tag, index):
            value_v = compact_2012_dac.getValueFromDAC20(index)
            self.f_comments.write(f"dac={iDac_index}: {tag}={index} ({value_v:0.9f} V)\n")

        print2("argmin", argmin)
        print2("argmax", argmax)
        # self.f_comments.write(f'dac={iDac_index}: argmax={iDacStart+argmax} ({compact_2012_dac.getValueFromDAC20(iDacStart+argmax):0.9f} V), argmin={iDacStart+argmin} ({compact_2012_dac.getValueFromDAC20(iDacStart+argmin):0.9f} V)\n')

    def save(self):
        np.savez_compressed(self.filename_npz, data=self.data, data_f_DAC12_int_per_V=self.data_f_DAC12_int_per_V)
        # np.savez(filename, data=self.data)
        with open(self.filename_txt, "w") as f:
            f.write(self.f_comments.getvalue())

    def load(self):
        """return the calibration-lookup-function"""
        if not os.path.exists(self.filename_npz):
            print("{}: Calibration data does not exist.".format(self.filename_npz))
            return None

        numpy_file = np.load(self.filename_npz)
        self.data = numpy_file["data"]
        self.data_f_DAC12_int_per_V = numpy_file["data_f_DAC12_int_per_V"]
        assert self.data.shape == (micropython_portable.DACS_COUNT, micropython_portable.DAC20_MAX)

        return self.calibrationLookup

    def calibrationLookup(self, iDac_index, dac20_value):
        """
        This function returns a DAC12 offset for every 'dac20_value'.
        """
        assert 0 <= iDac_index < micropython_portable.DACS_COUNT
        assert 0 <= dac20_value < micropython_portable.DAC20_MAX

        dac12_value = self.data[iDac_index, dac20_value]
        dac12_value = int(dac12_value)

        f_dac_12_int_per_V = self.data_f_DAC12_int_per_V[iDac_index]

        return f_dac_12_int_per_V, dac12_value
