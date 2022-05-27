# HeaterThermometrie2021


TODO: 2 PIN's to detect insert
TODO: Console window should not become visible!
DONE: Python 3.9 -> Only Python 3.7.9 is supported

## PID Controller

=temperature_calibrated=> (setpoint)controller(output)
    =power=> tail
        =voltage=> /3.3V
            =resitance=> calibration table
                => temperature_calibrated




## Defrost in micropython

100% heizen solange PT1000 R < 1116 Ohm # "PT1000 30C"

"Defrosting - do not open"

"Ready to remove vessel"

# Design HEATING

## Control

The labber combobox will signal the statemachine the change state.

In state HEATING CONTROLLED these values will be used:
  * ControlWriteTemperature_K
  * ControlWriteTemperatureToleranceBand_K
  * ControlWriteSettleTime_S
  * ControlWriteTimeoutTime_S

The settle time starts when switching from term_off to term_on(defrost/off/manual/controlled).


## Change of ControlWriteTemperatureAndSettle_K

ControlWriteTemperatureAndSettle_K is always set by the labber driver to -1K.
Setting ControlWriteTemperatureAndSettle_K will set ControlWriteTemperature_K.
Setting ControlWriteTemperatureAndSettle_K will reset error counter to 0.
Settrig ControlWriteTemperatureAndSettle_K will prevent counting errors till the command returns.

# Micropython standalone

Micropython starts in standalone mode:
The watchdog is initialized.
A timer will call `main.defrost_tick()` every second.
Every tick will reset the wathdog.

When the driver starts, it will call `main.enter_driver_mode` which stopps the timer.
`proxy.get_defrost()` will reset the watchdog.
When the driver is stopped, the watchdog will fire and we are back in standalone mode.

