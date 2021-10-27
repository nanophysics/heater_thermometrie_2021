# HeaterThermometrie2021

## Code Review

* Unit tests (pytest)
* Tail calibration
* Defrost standalone
* HEATING controlled
* Remove insert tail

TODO: Unit tests: Save screens
TODO: Console window should not become visible!
TODO: Python 3.9
TODO: Where to save logfile ?
TODO: Labber instrument server: Change combobox MANUAL/CONTROLLED

## PID Controller

=temperature_calibrated=> (setpoint)controller(output)
    =power=> tail
        =voltage=> /3.3V
            =resitance=> calibration table
                => temperature_calibrated



Wie kalibrieren?
  Peter macht numpy Beispiel

# DISPLAY
    1234567890123456
  a
  b
  c
  d
  e


* a
  * Temp calibrated
* b, c: Status
  * DISCONNECTED
  * THERMOFF
  * DEFROST
  * HEATING CONTROLLED
  * HEATING MANUAL
  * HEATING OFF
* d, e: Message 2 Zeilen
  * "Do not open !"
  * "Ready to open")

## Defrost in micropython
DONE:  100% heizen solange PT1000 R < 1116 Ohm # "PT1000 30C"
    "Defrosting - do not open"
    "Ready to remove vessel"


TODO: Bugfix
  INFO:LabberDriver:Waiting for 'ControlWriteTemperatureAndWait'. 0.5s: settled=True
    => Warum True?

DONE: Neu
  StatusReadSettled = "settled"
  StatusReadTimeout = "timeout"

DONE: Bugfix
  Experiment Fenster
   1. mal: Timeout
   2. mal: Antwort sofort
  Add unit test
