# pylint: disable=import-error
# pylint: disable=consider-using-f-string

import pyb
import machine
import micropython

import micropython_logic

_proxy = micropython_logic.Proxy()


def proxy():
    _proxy.defrost_process.pc_command()
    return _proxy


def blink(__dummy__):
    _proxy.tick()


timer = pyb.Timer(1, freq=1)
timer.callback(lambda timer: micropython.schedule(blink, None))


def reset():
    machine.reset()
