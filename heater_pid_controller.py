# -*- coding: utf-8 -*-

# https://github.com/pjkundert/ownercredit/blob/master/portable_pid_controller.py
config_app_time_delta_max_s = 10.0

PERSIST_PID_fI = "Pid.%s.fI"


class PidController:
    """
    Implements a PID control loop, but acts like a simple integer or float value in most use cases.
    Modulates fOutputValue based on proportional error between current fSensorValue value and desired fSetpoint.
    Automatically damps Integral term to avoid "wind-up", if fOutputValue is saturated.
    Auto-adjusts the initial Integral term to yield the desired steady-state fOutputValue, if the
    given initial fSensorValue value is maintained.  Output limits may be specified here, or
    may be provided on each invocation of loop().

    The initial 'fSetpoint' and 'fSensorValue' values provided are allowed to be simple scalar values, or
    may be more complex "filtered" values, based on misc.value.  If they provide a .sample(...)
    method it will be used to collect future .loop() fSetpoint and fSensorValue values.
    """

    def __init__(
        self,
        strName,
        time_now_s,
        # PID loop portable_constants
        fKp=1.0,
        fKi=1.0,
        fKd=1.0,
        # Initial fSetpoint
        fSetpoint=0.0,
        # fSensorValue value
        fSensorValue=0.0,
        # and fOutputValue
        fOutputValue=0.0,
    ):
        """
        Given the initial PID loop portable_constants Kpid, and fSetpoint, fSensorValue and target fOutputValue values,
        computes the appropriate instantaneous fP (Proportion) and fI (Integral) to yield the target
        fOutputValue.  This means that we will get a smooth fOutputValue value as we begin controlling, by
        avoiding a large instantaneous fD (rate of change of the error term) on startup.  This allows
        us to enter a fSensorValue already under way with a steady state PID control loop.
        """
        self.strName = strName
        self.PERSIST_PID_fI = PERSIST_PID_fI % strName
        self.fKp, self.fKi, self.fKd = fKp, fKi, fKd

        self.fSetpoint = fSetpoint
        self.fSensorValue = fSensorValue

        # Last time computed
        self.time_last_s = time_now_s

        # with this error proportion term
        self.fP = self.fSetpoint - self.fSensorValue
        self.fD = 0.0

        # Now, compute the required Integral to yield the desired initial steady-state fOutputValue.  We
        # have no proportion error (fP) history, and hence assume a 0 Derivative (fKd) term, so:
        #
        #   fOutputValue = fP * fKp + fI * fKi + fD * fKd
        #   fOutputValue = fP * fKp + fI * fKi + 0 * fKd
        #   fOutputValue - fP * fKp = fI * fKi
        #
        #   fOutputValue - fP * fKp
        #   --------------- = fI
        #       fKi
        if fKi > 0.0:
            self.fI = None
            if self.fI is None:
                self.fI = (fOutputValue - self.fP * self.fKp) / self.fKi
        else:
            self.fI = 0.0

        # Raw computed fOutputValue
        self.fOutputValueNotLimited = fOutputValue
        # Limited fOutputValue value
        self.fOutputValueLimited = fOutputValue
        self.bLimitHigh = False
        self.bLimitLow = False

    def process(
        self,
        # Time
        time_now_s,
        # Current fSetpoint
        fSetpoint,
        # Current fSensorValue value
        fSensorValue,
        # Output limiting (eg. fOutputValue saturated)
        fLimitOutLow,
        fLimitOutHigh,
        bAllowIncreaseI=True,
        bAllowDecreaseI=True,
    ):
        """
        Compute the new fOutputValue value, based on the latest fSetpoint and fSensorValue value.  Optionally
        perform fOutputValue limiting and Integral anti-windup (if fOutputValue is saturated).  We do fOutputValue
        limiting here (instead of remembering it in __init__), to allow for dynamic fOutputValue limits
        that change over time.
        """
        time_delta_s = time_now_s - self.time_last_s
        assert time_delta_s > 0.0
        self.time_last_s = time_now_s

        time_delta_s = min(time_delta_s, config_app_time_delta_max_s)

        # Compute change in fSetpoint over time_delta_s; we'll reduce the rate of change
        # derivative fD by the rate of change in fSetpoint, fDeltaSetpoint, because changing
        # our mind about the fSetpoint shouldn't result in an instantaneous large
        # rate of change in the error over the last interval!  Always use
        # operators to access self.fSetpoint, in case it's a misc.value
        fDeltaSetpoint = -self.fSetpoint
        self.fSetpoint = fSetpoint
        fDeltaSetpoint += self.fSetpoint

        self.fSensorValue = fSensorValue

        # New fSensorValue, fSetpoint and error term only contribute if time has elapsed!
        # Proportional: error between fSetpoint and fSensorValue value
        fP = self.fSetpoint - self.fSensorValue
        # Integral:   total error under curve over time
        fI = self.fI + fP * time_delta_s
        # Derivative:   instantanous rate of change of error (net fDeltaSetpoint)
        fD = (fP - self.fP - fDeltaSetpoint) / time_delta_s
        # (must remember for fD computation over time)
        self.fP = fP
        # (not necessary, but useful for monitoring)
        self.fD = fD

        # Compute tentative Output value, clamp Output to saturation limits, and perform
        # Integral anti-windup computation -- only remembering new Integral if fOutputValue value not
        # clamped (or if new Integral would reduce Output clamping)!  Remember, any comparison
        # against misc.nan is False.
        self.fOutputValueNotLimited = fP * self.fKp + fI * self.fKi + fD * self.fKd
        self.bLimitHigh = self.fOutputValueNotLimited > fLimitOutHigh
        self.bLimitLow = self.fOutputValueNotLimited < fLimitOutLow
        if self.bLimitLow:
            # Clamp fOutputValue on low end, only remember increasing Integral
            self.fOutputValueLimited = fLimitOutLow
            if fI > self.fI:
                self.fI = fI
            return time_delta_s

        if self.bLimitHigh:
            # Clamp fOutputValue on high end, only remember decreasing Integral
            self.fOutputValueLimited = fLimitOutHigh
            if fI < self.fI:
                self.fI = fI
            return time_delta_s

        # No clamping; use fOutputValue and Integral as-is
        self.fOutputValueLimited = self.fOutputValueNotLimited
        if (fI < self.fI) and bAllowDecreaseI:
            self.fI = fI
        if (fI > self.fI) and bAllowIncreaseI:
            self.fI = fI
        # self.fI = fI
        return time_delta_s
