# decompyle3 version 3.7.5
# Python bytecode 3.7 (3394)
# Decompiled from: Python 3.7.5 (tags/v3.7.5:5c02a39a0b, Oct 15 2019, 00:11:34) [MSC v.1916 64 bit (AMD64)]
# Embedded file name: SG_Object.py
# Compiled at: 2020-05-29 22:51:13
# Size of source mod 2**32: 1961 bytes
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import ascii, bytes, chr, dict, filter, hex, input, int, map, next, oct, open, pow, range, round, str, super, zip

def getConfigAsDict(obj, lKey):
    """Return the config as a dict"""
    dConfig = dict()
    for key in lKey:
        dConfig[key] = getattr(obj, key)

    return dConfig


def setConfigFromDict(obj, dConfig, lKey):
    """Set the config from a dict"""
    for key in lKey:
        setattr(obj, key, dConfig[key])


if __name__ == '__main__':
    pass