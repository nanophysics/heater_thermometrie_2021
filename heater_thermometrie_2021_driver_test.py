import time
import heater_thermometrie_2021_driver

if __name__ == '__main__':
    driver = heater_thermometrie_2021_driver.HeaderThermometrie2021()
    driver.sync_set_geophone_led_threshold_percent_FS(10.0)

    if False:
        while True:
            driver.sync_status_get()
            driver.debug_geophone_print()
            time.sleep(0.4)

    if False:
        start = time.time()
        COUNT = 200
        for i in range(COUNT):
            driver.sync_dac_set_all({0: {'f_DA_OUT_desired_V': -2.5,}})
            driver.sync_dac_set_all({0: {'f_DA_OUT_desired_V': 2.5,}})
        print('Average time for {}: {}ms'.format(COUNT, (time.time()-start)/COUNT/2.0*1000.0))

    if True:
        import random

        for i in range(10000000):
            if i % 1000 == 0:
                print(i)
            f_DA1 = random.uniform(4.5, 5.5)
            f_DA2 = random.uniform(-4.5, -5.5)
            f_DAx = random.uniform(-10.0, 10.0)
            d = {}
            for i, f in enumerate((f_DA1, f_DA2, f_DAx, f_DAx, f_DAx, f_DAx, f_DAx, f_DAx, f_DAx, f_DAx)):
                d[i] = {'f_DA_OUT_desired_V': f,}
            driver.sync_dac_set_all(d)

    for f_DA_OUT_desired_V in (-2.0, 0.0, 2.0):
        driver.sync_dac_set_all({
            0: {'f_DA_OUT_desired_V': f_DA_OUT_desired_V, 'f_gain': 0.5, },
            1: {'f_DA_OUT_desired_V': -f_DA_OUT_desired_V, 'f_gain': 0.5, },
        })
        pass


    def set(dict_requested_values):
        start_s = time.perf_counter()
        while True:
            b_done, dict_changed_values = driver.sync_dac_set_all(dict_requested_values)
            print('{:3.1f}%, dict_changed_values: {}'.format(driver.get_geophone_percent_FS(), dict_changed_values))
            if b_done:
                print('done {:3.1f}ms'.format(1000.0*(time.perf_counter() - start_s)))
                break

    set({
        0: {
          'f_DA_OUT_desired_V': 6.0,
        },
        1: {
          'f_DA_OUT_desired_V': 6.5,
          'f_gain': 0.5,
        },
        2: {
          'f_DA_OUT_desired_V': 6.0,
          'f_gain': 0.2,
        },
    })
  
    # 1: (6.5V-1.5V)/2.5V/s = 2s
    set({
        0: {
          'f_DA_OUT_desired_V': 2.5,
          'f_DA_OUT_sweep_VperSecond': 5.0,
        },
        1: {
          'f_DA_OUT_desired_V': 1.5,
          'f_DA_OUT_sweep_VperSecond': 2.5,
          'f_gain': 0.5,
        },
        2: {
          'f_DA_OUT_desired_V': 5.0,
          'f_gain': 0.2,
        },
    })

    set({
        0: {
          'f_DA_OUT_desired_V': 2.0,
          'f_DA_OUT_sweep_VperSecond': 1.0,
        },
        2: {
          'f_DA_OUT_desired_V': 10.0,
          'f_gain': 0.2,
        },
    })
    
    driver.close()
