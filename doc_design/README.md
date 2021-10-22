# HeaterThermometrie2021

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
  100% heizen solange PT1000 R < 1116 Ohm # "PT1000 30C"
    "Defrosting - do not open"
    "Ready to remove vessel"


TODO: Bugfix
  INFO:LabberDriver:Waiting for 'ControlWriteTemperatureAndWait'. 0.5s: settled=True
    => Warum True?

TODO: Neu
  StatusReadSettled = "settled"
  StatusReadTimeout = "timeout"

TODO: Bugfix
  Experiment Fenster
   1. mal: Timeout
   2. mal: Antwort sofort
  Add unit test
  TODO: Fix unit test