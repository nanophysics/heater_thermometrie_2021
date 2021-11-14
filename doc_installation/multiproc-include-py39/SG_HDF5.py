# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: SG_HDF5.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 8874 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
dict0 = dict
bytes0 = bytes
from builtins import ascii, bytes, chr, dict, filter, hex, input, int, map, next, oct, open, pow, range, round, str, super, zip
import sys, numpy as np, h5py
PY2 = sys.version_info < (3, )
PY3 = sys.version_info > (3, )

def createEnumDatatype(lNames):
    """Create an enum datatype for use in hdf5 tables"""
    dRange = dict0(zip(lNames, range(len(lNames))))
    return h5py.special_dtype(enum=(np.int16, dRange))


def createStrDatatype():
    """Create an string datatype for use in hdf5 tables"""
    return h5py.special_dtype(vlen=(str if PY3 else unicode))


def createDatatypeForDataset(lKeys, lDatatype):
    """Create a numpy datatype representing a record dataset in h5py"""
    if PY2:
        lKeys = [s.encode('utf-8') for s in lKeys]
    return np.dtype(list(zip(lKeys, lDatatype)))


def encodeAttribute(data):
    """Encode data into correct np datatype for hdf5 attributes"""
    if isinstance(data, (list, tuple)):
        if len(data) > 0 and isinstance(data[0], str):
            if PY3:
                dtu = h5py.special_dtype(vlen=str)
                return np.array(data, dtu)
            dtu = h5py.special_dtype(vlen=unicode)
            return np.array([unicode(x) for x in data], dtu)
        else:
            return data
    else:
        if isinstance(data, str):
            if PY3:
                return data
            return unicode(data)
        if data is None:
            if PY3:
                return 'NoneValue'
            return unicode('NoneValue')
        return data


def decodeAttribute(data):
    """Decode bytes to string in input data structure for hdf5"""
    if isinstance(data, str):
        if data == 'NoneValue':
            return
        return data
    if isinstance(data, np.ndarray):
        if data.dtype.type is np.bytes_:
            return [element.decode('utf-8') for element in data]
        if data.dtype.type is np.object_:
            return [str(element) for element in data]
        return data
    if isinstance(data, (bytes, np.bytes_)):
        s = data.decode('utf-8')
        if s == 'NoneValue':
            return
        return s
    if isinstance(data, (np.bool_,)):
        return bool(data)
    return data


def setAttribute(hdf_ref, name, value):
    """Set attribute of hdf_ref, taking care encoding str to bytes"""
    hdf_ref.attrs[name] = encodeAttribute(value)


def getAttribute(hdf_ref, name):
    """Set attribute of hdf_ref, taking care decoding bytes to str"""
    return decodeAttribute(hdf_ref.attrs[name])


def getAttributeDef(hdf_ref, name, default=None):
    """Set attribute of hdf_ref, taking care decoding bytes to str"""
    if name not in hdf_ref.attrs:
        return default
    return decodeAttribute(hdf_ref.attrs[name])


def createAttributesFromDict(hdfObj, dObj):
    """Add/overwrite attributes of an hdf5 object"""
    for key, value in dObj.items():
        hdfObj.attrs[key] = encodeAttribute(value)


def readAttributesToDict(hdfObj):
    """Get the attributes from a hdfObj and put them in a dict"""
    dData = dict()
    for key, value in hdfObj.attrs.items():
        dData[key] = decodeAttribute(value)

    return dData


def convertIfEnum(value, dt):
    """ Converts the data to integer if datatype is enum, also encode strings"""
    try:
        dMap = h5py.check_dtype(enum=dt)
    except Exception:
        dMap = None

    if dMap is not None:
        value = dMap.get(value, 0)
    if PY2:
        if isinstance(value, str):
            value = unicode(value)
    return value


def convertFromEnum(value, dt):
    """If dt is enum, convert the hdf value to its enum string, also decode bytes"""
    try:
        dMap = h5py.check_dtype(enum=dt)
    except Exception:
        dMap = None

    if dMap is not None:
        inv_map = {v:k for k, v in dMap.items()}
        value = inv_map[value]
    value = value.decode('utf-8') if isinstance(value, bytes) else value
    return value


def createRecordFromDictList(hdfRef, sName, lDict, lKeys, lDatatype):
    """Create a record dataset in a hdf5 file.  The data is taken from the key
    member variables from a list of objects"""
    dt_stepItem = createDatatypeForDataset(lKeys, lDatatype)
    hdfDS = hdfRef.create_dataset(sName, (len(lDict),), dtype=dt_stepItem)
    for n, dObj in enumerate(lDict):
        lVal = []
        for key, dt in zip(lKeys, lDatatype):
            value = dObj[key]
            value = convertIfEnum(value, dt)
            lVal.append(value)

        hdfDS[n] = tuple(lVal)


def readRecordToDictList(hdf_DS):
    """Read record to dict list, using the data format given by the hdf file"""
    lDict = []
    lField = hdf_DS.dtype.fields.keys()
    mD = hdf_DS[:]
    lDict = [{field:convertFromEnum(data[field], hdf_DS.dtype[field]) for field in lField} for data in mD]
    return lDict


def createHdf5FromObjectList(hdfRef, sName, lObj, lKeys, lDatatype):
    """Create a record dataset in a hdf5 file.  The data is taken from the key
    member variables from a list of objects"""
    dt_stepItem = createDatatypeForDataset(lKeys, lDatatype)
    hdfDS = hdfRef.create_dataset(sName, (len(lObj),), dtype=dt_stepItem)
    for n, obj in enumerate(lObj):
        lVal = []
        for key, dt in zip(lKeys, lDatatype):
            value = getattr(obj, key)
            value = convertIfEnum(value, dt)
            lVal.append(value)

        hdfDS[n] = tuple(lVal)


def createStringTable(hdfRef, sName, lText):
    """Create table for storing text from a list of tuples"""
    dt_str = createStrDatatype()
    n = 0 if len(lText) == 0 else max([len(x) for x in lText])
    hdfDS = hdfRef.create_dataset(sName, (len(lText),), dtype=dt_str)
    for n, lStr in enumerate(lText):
        s = '/'.join(lStr)
        hdfDS[n] = unicode(s) if PY2 else s


def readStringTable(hdfRef):
    """Read string table into list of tuples"""
    mD = hdfRef[:]
    lOut = []
    for data in mD:
        data = data.decode('utf-8') if isinstance(data, bytes) else data
        lOut.append(tuple(data.split('/')))

    return lOut


if __name__ == '__main__':
    a = createEnumDatatype(['None'])
    b = a()