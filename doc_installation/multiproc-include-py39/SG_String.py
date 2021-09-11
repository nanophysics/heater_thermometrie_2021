# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: SG_String.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 11192 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import ascii, bytes, chr, dict, filter, hex, input, int, map, next, oct, open, pow, range, round, str, super, zip
import numpy as np, json, base64

class NumpyBinaryJSONEncoder(json.JSONEncoder):
    __doc__ = 'JSON encoder that handles numpy arrays nicely'

    def default(self, obj):
        """If input object is an ndarray it will be converted into a dict
        holding dtype, shape and the data, base64 encoded.
        """
        if isinstance(obj, (complex, np.complex128, np.complex64, np.complex_)):
            return dict(__complex__=(obj.real, obj.imag))
        if isinstance(obj, np.ndarray):
            if obj.flags['C_CONTIGUOUS']:
                obj_data = obj.data
            else:
                cont_obj = np.ascontiguousarray(obj)
                assert cont_obj.flags['C_CONTIGUOUS']
                obj_data = cont_obj.data
            obj_data = base64.b64encode(obj_data)
            return dict(__ndarray__=(obj_data.decode()), dtype=(str(obj.dtype)),
              shape=(obj.shape))
        if isinstance(obj, (np.generic,)):
            return obj.tolist()
        return json.JSONEncoder(self, obj)


def json_numpy_obj_hook(dct):
    """Decodes a previously encoded numpy ndarray with proper shape and dtype.

    :param dct: (dict) json encoded ndarray
    :return: (ndarray) if input was an encoded ndarray
    """
    if isinstance(dct, dict):
        if '__ndarray__' in dct:
            data = base64.b64decode(dct['__ndarray__'])
            return np.frombuffer(data, dct['dtype']).reshape(dct['shape'])
        if '__complex__' in dct:
            return complex(*dct['__complex__'])
    return dct


class NumpyTextJSONEncoder(json.JSONEncoder):
    __doc__ = 'JSON encoder that handles numpy arrays nicely'

    def default(self, obj):
        """If input object is an ndarray it will be converted into a dict
        holding dtype, shape and the data as list.
        """
        if isinstance(obj, (complex, np.complex128, np.complex64, np.complex_)):
            return dict(__complex__=(obj.real, obj.imag))
        if isinstance(obj, np.ndarray):
            if not obj.flags['C_CONTIGUOUS']:
                obj = np.ascontiguousarray(obj)
                assert obj.flags['C_CONTIGUOUS']
                return dict(__ndarray__=(obj.flatten().tolist()), dtype=(str(obj.dtype)),
                  shape=(obj.shape))
        if isinstance(obj, (np.generic,)):
            return obj.tolist()
        return json.JSONEncoder(self, obj)


def json_numpy_text_hook(dct):
    """Decodes a previously encoded numpy ndarray with proper shape and dtype.

    :param dct: (dict) json encoded ndarray as text
    :return: (ndarray) if input was an encoded ndarray
    """
    if isinstance(dct, dict):
        if '__ndarray__' in dct:
            dtype = dct.get('dtype', 'float')
            if 'shape' in dct:
                return np.array(dct['__ndarray__'], dtype).reshape(dct['shape'])
            return np.array(dct['__ndarray__'], dtype)
        elif '__complex__' in dct:
            return complex(*dct['__complex__'])
    return dct


def dump_to_json_numpy_text(obj):
    """Encode obj to json file with numpy data as pure text"""
    return json.dumps(obj, cls=NumpyTextJSONEncoder, sort_keys=True, indent=4).encode('utf-8')


def load_from_json_numpy_text(data):
    """Decode data from input containing json file encoded as text"""
    return json.loads((data.decode('utf-8')), object_hook=json_numpy_text_hook)


def encodeMsgPack(obj):
    """Binary encoding for msgpack
    """
    if isinstance(obj, (complex, np.complex128, np.complex64, np.complex_)):
        return dict(__complex__=(obj.real, obj.imag))
    if isinstance(obj, np.ndarray):
        obj_data = obj.tobytes('C')
        return dict(__ndarray__=obj_data, dtype=(str(obj.dtype)),
          shape=(obj.shape))
    if isinstance(obj, (np.generic,)):
        return obj.tolist()
    return obj


def decodeMsgPack(dct):
    """Decodes a previously encoded numpy ndarray with proper shape and dtype.

    :param dct: (dict) json encoded ndarray
    :return: (ndarray) if input was an encoded ndarray
    """
    if isinstance(dct, dict):
        if '__ndarray__' in dct:
            data = dct['__ndarray__']
            return np.frombuffer(data, dct['dtype']).reshape(dct['shape'])
        if '__complex__' in dct:
            return complex(*dct['__complex__'])
    return dct


def getSIPrefix(value, sUnit='', iDecimals=3, iDim=1, iPot=None, bExpIfNoUnit=False):
    """[sAll, sPrefix, newValue, dScale, sExpNot] = STRING_GetSIPrefix(value, sUnit, iDecimals, iDim, iPot)
    #   Returns a string containing the prefix for given value. The prefix is
    #   given for every third power of ten, with the output numeric value
    #   ranging from 1-999.
    #   Optional arguments:
    #   if sUnit is given, the unit will be added to the outputs
    #   iDecimals specifies number of decimals given in sAll output string
    #   iDim states dimension of value, for a volume, iDim should equal 3
    #   If iPot is given, the function will output the prefix corrsponding to
    #   10^iPot. For iPot, prefices are also given for 10^-2 and 10^-1
    #   If bExpIfNoUnit is True, sAll will be on exponential notation
    """
    if isinstance(value, str):
        return (value, '', value, 1, value)
    if np.isnan(value):
        return ('NaN', '', value, 1, 'NaN')
    if value == float('inf'):
        return ('Inf', '', value, 1, 'Inf')
    if value == float('-inf'):
        return ('-Inf', '', value, 1, '-Inf')
    if iDecimals < 3:
        iDecimals = 3
    cPrefix = [
     'y', 'z', 'a', 'f', 'p', 'n', 'u', 'm', '', 'k', 'M', 'G', 'T', 'P']
    if iPot is not None:
        if iPot == -1 or iPot == -2:
            cPrefix = [
             'c', 'd']
            sPrefix = cPrefix[(iPot + 2)]
        else:
            iPot = 3 * np.floor(iPot / 3.0)
            sPrefix = cPrefix[int(round(iPot // 3 + 8))]
        iPot = iPot * iDim
    else:
        if value != 0:
            sTmp = '%%.%de' % (iDecimals - 1) % value
            iE = sTmp.upper().find('E')
            if iE < 0:
                iPot = 0
            else:
                iPot = int(sTmp[iE + 1:])
                iPot = 3 * iDim * np.floor(iPot / (3.0 * iDim))
        else:
            iPot = 0
        indx = iPot // (3 * iDim) + 8
        if indx >= 0 and indx < len(cPrefix):
            sPrefix = cPrefix[int(round(iPot // (3 * iDim) + 8))]
        else:
            sPrefix = 'E%d' % iPot
    dScale = 1.0 / 10.0 ** iPot
    newValue = value * dScale
    if sUnit == '':
        sConv = '%%.%dg%s' % (iDecimals, sPrefix)
    else:
        sConv = '%%.%dg %s' % (iDecimals, sPrefix)
    sAll = sConv % newValue
    sAll += sUnit
    if iPot == 0:
        sConv = '%%.%dg' % iDecimals
    else:
        sConv = '%%.%dgE%d' % (iDecimals, iPot)
    sExpNot = sConv % newValue
    if bExpIfNoUnit:
        if sUnit == '':
            sAll = sExpNot
    return (
     sAll, sPrefix, newValue, dScale, sExpNot)


def getEngineeringString(value, iDigits=3):
    """ sExpNot = STRING_GetEngineeringString(value, iDigits)
    returns a string in engineering form (in 3-decade potentials)
    """
    if value != 0:
        sTmp = '%%.%de' % (iDigits - 1) % value
        iE = sTmp.upper().find('E')
        if iE < 0:
            iPot = 0
        else:
            iPot = int(sTmp[iE + 1:])
            iPot = 3 * np.floor(iPot / 3.0)
    else:
        iPot = 0
    if iPot == 0 or np.isnan(value):
        sConv = '%%.%dg' % iDigits
    else:
        sConv = '%%.%dgE%d' % (iDigits, iPot)
    sExpNot = sConv % (value / 10.0 ** iPot)
    return sExpNot


def getValueFromSIString(sSI):
    """Returns a float with the value encoded in a SI-type string. 

    The function assumes the string to contain either a number or a number
    followed by an SI-prefix, otherwise it returns None"""
    sSI = sSI.strip()
    if len(sSI) == 0:
        return 0.0
    try:
        cPrefix = ['y', 'z', 'a', 'f', 'p', 'n', 'u', 'm', None, 'k', 'M', 'G', 'T', 'P']
        if sSI[(-1)] in cPrefix:
            iPot = 3 * (cPrefix.index(sSI[(-1)]) - 8)
            return float(sSI[:-1]) * 10 ** iPot
        if sSI[(-1)].isdigit() or (sSI[(-1)] == '.'):
            return float(sSI)
        return
    except ValueError:
        return


def getTimeString(sec):
    """Return a H:M:S string from the input sec"""
    m, sec = divmod(sec, 60)
    h, m = divmod(m, 60)
    return '%d:%02d:%02d' % (h, m, sec)


if __name__ == '__main__':
    print(getValueFromSIString(''))
    sAll, sPrefix, newValue, dScale, sExpNot = getSIPrefix((-0.9999), sUnit='', iDecimals=3, iDim=1, iPot=None)
    print(sAll, sPrefix, sExpNot)
    sAll, sPrefix, newValue, dScale, sExpNot = getSIPrefix(0.9999, sUnit='', iDecimals=3, iDim=1, iPot=None)
    print(sAll, sPrefix, sExpNot)
    print(getEngineeringString(0.999))