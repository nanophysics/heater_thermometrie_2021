"""
  This runs on Micropython and on the PC!
"""
import binascii

# Analog limit of differential amplifier
fADC24_LIMIT_V = 0.7e-3  # corresponds to +- 1.4V at the ADC24 input

# DACS in compact2012
DACS_COUNT = 10
# Maximal output
VALUE_PLUS_MIN_MAX_V = 10.0

# AD5791 20 bit
# These are the registers of the 20 bit dac
DAC20_NIBBLES = 5
DAC20_BITS = DAC20_NIBBLES * 4
DAC20_MAX = 2 ** DAC20_BITS
# '{:05X}' => '00000', '80000', 'A6666'
DAC20_FORMAT_HEX = "{:0" + str(DAC20_NIBBLES) + "X}"

# AD5300  12 bit
# These are the registers of the 12 bit dac.
# The 12 bits are used as follows
# B11, B10: 0  These 2 bits may be used later using lookup-tables for linearity control
# B9 .. B0: x  These 10 bits are used to enhance the resolution of the last bit of the DAC20.
DAC12_NIBBLES = 3
DAC12_BITS = DAC12_NIBBLES * 4
DAC12_MAX = 2 ** DAC12_BITS
# '{:03X}' => '000', '800', 'A66'
DAC12_FORMAT_HEX = "{:0" + str(DAC12_NIBBLES) + "X}"

DAC12_MAX_CORRECTION_VALUE = DAC12_MAX - 2 ** 10

# DAC20 and 10 bits from DAC12
DAC30_MAX = 2 ** 30

# The registers of the DAC20. These registers are described here:
#   https://www.analog.com/media/en/technical-documentation/data-sheets/ad5791.pdf "Table 10. DAC Register"
DAC20_REGISTER_BYTES = 3
DAC20_REGISTER_NIBBLES = 2 * DAC20_REGISTER_BYTES

# This bitfield will be shifted through all 10 DAC20
dac20_nibbles = bytearray(DACS_COUNT * DAC20_REGISTER_NIBBLES)

# This bitfield will be shifted through all 10 DAC12
# A: The DAC12-shift-register will be sourced from the DAC20 shift-register.
# B: The last shift through the DAC12 is special.
#    Therefore 'dac12_bytes_value1to9' and 'dac12_bytes_value10'
dac12_nibbles = bytearray(DACS_COUNT * DAC20_REGISTER_NIBBLES)


def clear_dac_nibbles(init="3"):
    """
    Initialize the shift-register
    Init with 3 to see what is not initialized.
    """
    ord_init = ord(init)
    for i in range(len(dac20_nibbles)):
        dac12_nibbles[i] = dac20_nibbles[i] = ord_init


clear_dac_nibbles(init="3")


def set_dac20_nibbles(str_dac20):
    """
    str_dac20: '00000400006666673333800008CCCC99999C0000FFFFFFFFFF'

    'str_dac20' is the HEX-string we get from the PC.
    We reassemble it to fit into the DAC20 shift registers.
    'binascii.unhexlify(dac20_nibbles)' will the be sent to DAC20.
    """
    assert len(str_dac20) == DACS_COUNT * DAC20_NIBBLES

    # DAC20
    for i in range(DACS_COUNT):
        i_offset_in = (DACS_COUNT - 1 - i) * DAC20_NIBBLES
        i_offset_out = i * DAC20_REGISTER_NIBBLES

        dac20_nibbles[i_offset_out] = ord("1")
        for i in range(DAC20_NIBBLES):
            dac20_nibbles[i_offset_out + i + 1] = ord(str_dac20[i_offset_in + i])


def set_dac12_nibbles(str_dac12):
    """
    str_dac12: '0000002663330000CC1990003FF3FF'

    'str_dac12' is the HEX-string we get from the PC.
    We reassemble it to fit into the DAC20 shift registers.
    'binascii.unhexlify(dac12_nibbles)' will the be sent to DAC12.
    """
    assert len(str_dac12) == DACS_COUNT * DAC12_NIBBLES

    # DAC12
    for i in range(DACS_COUNT):
        i_offset_in = (DACS_COUNT - 1 - i) * DAC12_NIBBLES
        i_offset_out = i * DAC20_REGISTER_NIBBLES

        # x=0, x=0, PD1=0, PD0=0, D11=0, D10=0, D9, D8
        # D7, D6, D5, D4, D3, D2, D1=0, D0=0
        dac12_nibbles[i_offset_out + 0] = ord("0")
        for i in range(DAC12_NIBBLES):
            dac12_nibbles[i_offset_out + i + 1] = ord(str_dac12[i_offset_in + i])


def splice_dac12(dac12_nibbles):
    dac12_bytes = binascii.unhexlify(dac12_nibbles)
    bytes_count = (DACS_COUNT - 1) * DAC20_REGISTER_BYTES
    dac12_bytes_value1to9 = dac12_bytes[:bytes_count]
    dac12_bytes_value10 = dac12_bytes[bytes_count:]
    assert len(dac12_bytes_value1to9) == (DACS_COUNT - 1) * DAC20_REGISTER_BYTES
    assert len(dac12_bytes_value10) == DAC20_REGISTER_BYTES
    return dac12_bytes_value1to9, dac12_bytes_value10


def getHexStringFromListInt20(list_i_dac20):
    # list_i_dac20 = (0x02, 0xF87, ...)
    str_dac20 = "".join(map(DAC20_FORMAT_HEX.format, list_i_dac20))
    # str_dac20: '00000400006666673333800008CCCC99999C0000FFFFFFFFFF'
    return str_dac20


def getHexStringFromListInt12(list_i_dac12):
    # list_i_dac12 = (0x02, 0xF87, ...)
    str_dac12 = "".join(map(DAC12_FORMAT_HEX.format, list_i_dac12))
    # str_dac12: '0000001990CC0003332660003FF3FF'
    return str_dac12


#
# Logic for 'calib_' only
#
def convert_ADC24_signed_to_V(iADC24_signed):
    assert isinstance(iADC24_signed, int)
    gain_AD8428 = 2000.0
    factor = 3.3 / (2.0 ** 23) / gain_AD8428

    fADC24 = iADC24_signed * factor

    if not (-fADC24_LIMIT_V < fADC24 < fADC24_LIMIT_V):
        raise Exception("fADC24={:12.9f} but should be between {:12.9f} and {:12.9f}.".format(fADC24, -fADC24_LIMIT_V, fADC24_LIMIT_V))

    return fADC24


CALIB_RAW_FILETYPE = "CALIB_RAW_FILETYPE"
CALIB_RAW_VERSION = "CALIB_RAW_VERSION"
CALIB_RAW_SERIAL = "CALIB_RAW_SERIAL"
CALIB_RAW_DAC_START_I = "CALIB_RAW_DAC_START_I"
CALIB_RAW_DAC_A_INDEX = "CALIB_RAW_DAC_A_INDEX"
CALIB_RAW_FILETYPE_LIMP = "CALIB_RAW_FILETYPE_LIMP"


class CalibRawFileWriter:
    def __init__(self, filename, serial, iDacStart, iDacA_index):
        assert isinstance(iDacStart, int)
        assert isinstance(iDacA_index, int)
        dict_config = {}
        dict_config[CALIB_RAW_FILETYPE] = CALIB_RAW_FILETYPE_LIMP
        dict_config[CALIB_RAW_VERSION] = "1.0"
        dict_config[CALIB_RAW_SERIAL] = serial
        dict_config[CALIB_RAW_DAC_START_I] = iDacStart
        dict_config[CALIB_RAW_DAC_A_INDEX] = iDacA_index

        self.f = open(filename, "w")
        self.f.write(str(dict_config))
        self.f.write("\n")
        self.iDacStart = iDacStart

    def write(self, list_iAD24):
        self.f.write(",".join("{:X}".format(iAD24) for iAD24 in list_iAD24))
        self.f.write("\n")

    def close(self):
        self.f.close()
        self.f = None


class CalibRawFileReader:
    def __init__(self, filename):
        self.f = open(filename, "r")
        str_dict = self.f.readline()
        dict_config = eval(str_dict)
        self.iDacStart = dict_config[CALIB_RAW_DAC_START_I]
        self.iDacA_index = dict_config[CALIB_RAW_DAC_A_INDEX]

    def values(self):
        list_step_a_V = []
        list_step_b_V = []

        def get_step_V():
            line = self.f.readline()
            line = line.strip()
            if line is None:
                raise StopIteration()
            if len(line) == 0:
                # Empty line at the end of the file
                raise StopIteration()
            list_str = line.split(",")
            list_i = [int(s, 16) for s in list_str]
            list_V = [convert_ADC24_signed_to_V(signed) for signed in list_i]
            step_V = sum(list_V) / len(list_V)
            return step_V

        step_a_V = get_step_V()

        try:
            while True:
                step_b_V = get_step_V()
                tmp_ = step_b_V - step_a_V
                # Assign below. This make shure, that both array have the same size

                step_a_V = get_step_V()
                list_step_a_V.append(step_b_V - step_a_V)

                list_step_b_V.append(tmp_)
        except StopIteration:
            pass

        return list_step_a_V, list_step_b_V
