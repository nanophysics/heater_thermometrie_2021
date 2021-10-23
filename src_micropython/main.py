# pylint: disable=import-error
# pylint: disable=consider-using-f-string

import pyb
import machine
import micropython

import micropython_logic

proxy = micropython_logic.Proxy()


def blink(__dummy__):
    proxy.tick()


timer = pyb.Timer(1, freq=1)
timer.callback(lambda timer: micropython.schedule(blink, None))


def reset():
    machine.reset()
