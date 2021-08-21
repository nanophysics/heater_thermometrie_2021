#!/usr/bin/env python

import InstrumentDriver

import compact_2012_driver

class Driver(InstrumentDriver.InstrumentWorker):
    """ This class implements the Compact 2012 driver"""

    def performOpen(self, options={}):
        """Perform the operation of opening the instrument connection"""

        # open connection
        self.compact2012 = compact_2012_driver.HeaterThermometrie2021(hwserial=self.comCfg.address) 
    
        # Reset the usb connection (it must not change the applied voltages)
        self.log('ETH Compact Driver: Connection resetted at startup')

    def performClose(self, bError=False, options={}):
        """Perform the close instrument connection operation"""
        self.compact2012.close()

    def performSetValue(self, quant, value, sweepRate=0.0, options={}):
        """Perform the Set Value instrument operation. This function should
        return the actual value set by the instrument"""
        # keep track of multiple calls, to set multiple voltages efficiently
        if self.isFirstCall(options):
            self.dict_requested_values = {}
                # 0: {
                #     'f_DA_OUT_desired_V': 2.5,
                #     'f_DA_OUT_sweep_VperSecond': 5.0,
                #     'f_gain': 0.1
                # },
        if quant.name == 'Green LED':
            # set user LED
            self.compact2012.sync_set_user_led(bool(value))            
        elif quant.name.endswith('-voltage'):
            # get index of channel to set
            # Hack...
            # Parse quant.name="DA3-voltage" -> 3 -> 2
            indx0 = int(quant.name.strip().split('-')[0][2:]) - 1
            # don't set, just add to dict with values to be set (value, rate)
            str_gain = self.getValue('DA%d-jumper setting' % (indx0+1))
            f_gain = compact_2012_driver.DICT_GAIN_2_VALUE[str_gain]
            f_max_range = compact_2012_driver.VALUE_PLUS_MIN_MAX_V*f_gain
            value = min(f_max_range, max(-f_max_range, value))
            self.dict_requested_values[indx0] = {
                'f_DA_OUT_desired_V': value,
                'f_DA_OUT_sweep_VperSecond': sweepRate,
                'f_gain': f_gain,
            }
        elif quant.name.endswith('-jumper setting'):
            # get index of channel to set
            # Hack...
            # Parse quant.name="DA3-jumper" -> 3 -> 2
            indx0 = int(quant.name.strip().split('-')[0][2:]) - 1
            # read corresponding voltage to update scaling
            quant.setValue(value)
            self.readValueFromOther('DA%d-voltage' % (indx0+1))
        # if final call and voltages have been changed, send them at once
        elif quant.name == 'red LED threshold percent FS':
            value = max(0.0, min(100.0, value))
            self.compact2012.sync_set_geophone_led_threshold_percent_FS(value)
        if self.isFinalCall(options) and len(self.dict_requested_values)>0:
            self.sync_DACs()
        return value

    def sync_DACs(self):
        """Set multiple values at once, with support for sweeping"""
        while True:
            b_done, dict_changed_values = self.compact2012.sync_dac_set_all(self.dict_requested_values)
            # print('dict_changed_values: {}'.format(dict_changed_values))
            for indx0, value in dict_changed_values.items():
                # update the quantity to keep driver up-to-date
                # return the sweep-rate. If not defined - which should never happen, return 0.001
                sweepRate = self.dict_requested_values.get(indx0, {'f_DA_OUT_sweep_VperSecond': 0.001}).get('f_DA_OUT_sweep_VperSecond', 0.001)
                self.setValue('DA%d-voltage' % (indx0+1), value, sweepRate=sweepRate)
            if b_done:
                break
            # check if stopped 
            if self.isStopped():
                return

    def checkIfSweeping(self, quant):
        """Always return false, sweeping is done in loop"""
        return False

    def performGetValue(self, quant, options={}):
        """Perform the Get Value instrument operation"""
        # only implmeneted for geophone voltage
        if quant.name == 'percent FS':
            value = self.compact2012.get_geophone_percent_FS()
        elif quant.name == 'particle velocity':
            value = self.compact2012.get_geophone_particle_velocity()
        elif quant.name == 'red LED threshold percent FS':
            value = quant.getValue()
        elif quant.name.endswith('-voltage'):
            # get index of channel to get
            # Hack...
            # Parse quant.name="DA3-voltage" -> 3 -> 2
            indx0 = int(quant.name.strip().split('-')[0][2:]) - 1
            # get value from driver, then return scaled value
            str_gain = self.getValue('DA%d-jumper setting' % (indx0+1))
            gain = compact_2012_driver.DICT_GAIN_2_VALUE[str_gain]
            value = gain * self.compact2012.get_dac(indx0)
        else:
            # just return the quantity value
            value = quant.getValue()
        return value


if __name__ == '__main__':
    pass
