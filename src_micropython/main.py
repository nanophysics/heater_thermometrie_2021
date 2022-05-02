# pylint: disable=import-error

import pyb
import machine
import micropython
import micropython_logic

STANDALONE_TIMER_S = 1.0

proxy = micropython_logic.Proxy()


def defrost_tick(__dummy__):
    # Standalone mode:
    # The timer periodically calls the defrost process
    proxy.wdt_feed()
    proxy.defrost_process.tick()


timer = pyb.Timer(1, freq=STANDALONE_TIMER_S)
timer.callback(lambda timer: micropython.schedule(defrost_tick, None))


def enter_driver_mode():
    # Disable the timer (only relevant the first time)
    # Reset the watchdoc
    timer.callback(None)
    timer.deinit()


def reset():
    machine.reset()
