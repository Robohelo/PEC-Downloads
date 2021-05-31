# -*- coding: utf-8 -*-
"""
Created on Fri Feb 19 01:02:53 2021

@author: Roboadmin
"""
from adafruit_servokit import ServoKit
import Jetson.GPIO as GPIO
import temps
import threading
import time
import multiprocessing

# ds retry x3 J
# aknolage J
# Hum invert J
# Sleep
# GPIO.cleanup() J
# Wasser 10S not J
# safty mode ???
# Speicher Bilder


class PEC_HW():
    """
    Specificed Lib for PEC Project.
    includes:
    ---------
        __init__:
            sets servo channels

        xpos:
            sets pan

        ypos:
            sets tilt

        power:
            sets the Tempratur

        mist:
            sets humidity

    """

    def __init__(self):
        """
        Init PWM and set it to correct parameter.

        Returns
        -------
        None.

        """
        # set vars
        self.__deamon = True
        _tacho_pin = 'GPIO_PZ0'
        self._pow_pin = 'CAM_AF_EN'
        self._mist_pin = 'SPI2_MOSI'
        _pwm_pin = 'LCD_BL_PW'
        self._pwm_obj = None
        self._pump_pin = 'DAP4_DIN'
        self._sens_level_mist = 'UART2_CTS'
        self._sens_level_tank = 'DAP4_FS'
        self._sleep_pin = 'SPI2_SCK'
        self.__pow = 0
        self.__hum = 0
        self.__hum_temp = 100
        self.__sens_temp = 100
        self.__t = time.time()
        self.__rpm = 0

        # init everything
        GPIO.setmode(GPIO.TEGRA_SOC)
        GPIO.setup(self._pow_pin, GPIO.OUT)
        GPIO.setup(self._mist_pin, GPIO.OUT)
        GPIO.setup(self._pump_pin, GPIO.OUT)
        GPIO.setup(_tacho_pin, GPIO.IN)
        GPIO.setup(self._sens_level_mist, GPIO.IN)
        GPIO.setup(self._sens_level_tank, GPIO.IN)
        GPIO.setup(self._sleep_pin, GPIO.IN)
        GPIO.add_event_detect(_tacho_pin, GPIO.FALLING, self.__fan_int)
        GPIO.add_event_detect(self._sens_level_tank,
                              GPIO.BOTH, self.__tank)
        GPIO.add_event_detect(self._sleep_pin, GPIO.FALLING, self.__Sleep)
        self._tah = temps.Temp()
        self._led = LED()
        self.kit = ServoKit(channels=16)
        self.kit.servo[7].actuation_range = 180
        self.kit.servo[8].actuation_range = 20
        self._pwm_obj = GPIO.PWM(_pwm_pin, 1000)
        self.__mist_thread = threading.Thread(target=self.__mist_deamon)
        self.__pow_thread = threading.Thread(target=self.__pow_deamon)
        self.__pump_thread = threading.Thread(target=self.__pump_deamon)
        self.__mist_thread.start()
        self.__pow_thread.start()
        self.__pump_thread.start()
        self._pwm_obj.start(0)
        self._led.reset_error()

    def set_xpos(self, deg):
        """
        Sets first servo (servo for pan)
        to specific direction in degree.

        Parameters
        ----------
        deg : int (from -10 to 10)
            Sets direction in degrees.
            Zero is the the middle position.

        Returns
        -------
        None.

        """
        if deg < 0:
            deg = 0
        if deg > 90:
            deg = 90
        deg = deg*2
        self.kit.servo[7].angle = deg

    def set_ypos(self, deg):
        """
        Sets second servo (servo for tilt)
        to specific tilt in degree.

        Parameters
        ----------
        deg : int (from -10 to 10)
            Sets hight in degrees.
            Zero is the horizontal position.

        Returns
        -------
        None.

        """
        if deg < -10:
            deg = -10
        elif deg > 10:
            deg = 10
        deg += 10
        self.kit.servo[8].angle = deg

    def set_fan(self, speed):
        """
        Parameters
        ----------
        speed : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        if speed > 100:
            speed = 100
        elif speed < 0:
            speed = 0
        if speed < 19:
            speed = 0
            self.set_power(0)
            self.set_mist(0)
            time.sleep(3)
        self._pwm_obj.ChangeDutyCycle(speed)

    def get_fan(self):
        return int(self.__rpm)

    def set_power(self, power):
        """
        Set the power of the heating element.
        0-100 [%]

        Parameters
        ----------
        power : TYPE
            DESCRIPTION.

        Raises
        ------
        Exception
            DESCRIPTION.

        Returns
        -------
        None.

        """
        x = 0
        if power > 100:
            power = 100
        elif power < 0:
            power = 0
        if power != 0:
            while (self.__rpm < 100) and x < 3:
                time.sleep(1)
                x += 1
            if x > 3:
                print("Fan doesn't spinn!")
                return
        self.__pow = power

    def get_temp(self):
        return round(self._tah.get_hyt939(), 2)

    def set_mist(self, humidity):
        """
        Set the homidity of the air.
        0-100 [%]

        Parameters
        ----------
        humidity : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

        """
        if humidity > 100:
            humidity = 100
        elif humidity < 0:
            humidity = 0
        # could set acknolage
        self.__hum = humidity

    def get_hum(self):
        return round(self._tah.get_humidity(), 2)

# daemon

    def __pow_deamon(self):
        last_pow = 0
        max_temp = 60
        count_H = 0
        count_L = 0
        time.sleep(10)
        try:
            while(self.__deamon):
                if self.__pow != last_pow:
                    last_pow = self.__pow
                    print(last_pow)
                else:
                    target_temp = self._tah.get_DS18X20() + \
                        ((max_temp - self._tah.get_DS18X20()) / 100) * last_pow
                    if target_temp > max_temp - 10:
                        print(
                            "Tempratur input out of range (To High ({0}))".format(target_temp))
                    elif target_temp < 0:
                        print(
                            "Tempratur input out of range (To Low ({0}))".format(target_temp))
                is_temp = int(self._tah.get_hyt939())
                if is_temp > max_temp:
                    print(
                        "Tempratur sensor out of range (To High ({0}))".format(is_temp))
                elif is_temp < 0:
                    print(
                        "Tempratur sensor out of range (To Low ({0}))".format(is_temp))
                # Tempratur in target range
                #print("Temp:", is_temp, "\tOutput: ", end="")
                if((target_temp) < is_temp) or count_H > 5:
                    if(count_L > 5):
                        count_L = 0
                        count_H = 0
                    count_L += 1
                    # print("Low")
                    GPIO.output(self._pow_pin, GPIO.LOW)
                else:
                    # print("High")
                    GPIO.output(self._pow_pin, GPIO.HIGH)
                    count_H += 1
                #print("count_H: {0}, count_L: {1}".format(count_H, count_L))
                time.sleep(1)
        except Exception:
            print("Powerdeamon Dead")
            print(Exception.message)
            self._led.set_error()
        finally:
            GPIO.output(self._pow_pin, GPIO.LOW)

    def __mist_deamon(self):
        last_hum = 0
        while(self.__deamon):
            if self.__hum != last_hum:
                last_hum = self.__hum
                print(last_hum)
            else:
                target_hum = self.__hum
                if target_hum > 100:
                    target_hum = 100
                elif target_hum < 0:
                    target_hum = 0
            is_hum = self._tah.get_humidity()
            if(target_hum < is_hum):
                GPIO.output(self._mist_pin, GPIO.LOW)
            else:
                GPIO.output(self._mist_pin, GPIO.HIGH)
            time.sleep(1)
        GPIO.output(self._mist_pin, GPIO.LOW)

    def __pump_deamon(self):
        timeout = 0
        while(self.__deamon):
            if(GPIO.input(self._sens_level_mist) and not GPIO.input(self._sens_level_tank)):
                GPIO.output(self._pump_pin, GPIO.HIGH)
                timeout += 1
            else:
                GPIO.output(self._pump_pin, GPIO.LOW)
                timeout = 0
            if timeout > 10:
                raise TimeoutError("Timeout of Pump")
            time.sleep(1)
        GPIO.output(self._pump_pin, GPIO.LOW)

# Interrupts

    def __fan_int(self, channel):
        try:
            dt = time.time() - self.__t
            if dt < 0.005:
                return  # Reject spuriously short pulses
            freq = 1 / dt
            # Noctua fans puts out two pluses per revolution --> (freq/2)*60
            self.__rpm = (freq / 2) * 60
            self.__t = time.time()
        except:
            print("fan__init died")

    def __tank(self, channel):
        if GPIO.input(self._sens_level_tank):
            self._led.set_error()
            print("Tank emty")
        else:
            self._led.reset_error()
            print("Tank full")

    def __Sleep(self, channel):
        print("I am Sleeping")


# special functions

    def stop_daemon(self):
        self.__deamon = False
        self.__mist_thread.join()
        self.__pow_thread.join()
        self._tah._daemons_shutdown()
        GPIO.cleanup()
        print("successfully stoped daemons")


class LED():

    def __init__(self, pin='GPIO_PE6'):
        GPIO.setup(pin, GPIO.OUT)
        self.__pin = pin
        self.__error = 0
        self.__pwm = multiprocessing.Process()

    def __set_active(self):
        GPIO.output(self.__pin, GPIO.HIGH)

    def set_error(self):
        self.__error = 1
        if self.__pwm.is_alive():
            self.__pwm.terminate()
        else:
            self.__pwm = multiprocessing.Process(
                target=self.__pwm_daemon, args=(0.5, 0.5))

    def reset_error(self):
        if self.__pwm.is_alive():
            self.__pwm.terminate()
        self.__set_active()

    def set_sleep(self):
        if (self.__error == 0) and (not self.__pwm.is_alive()):
            self.__pwm = multiprocessing.Process(
                target=self.__pwm_daemon, args=(2, 1))

    def reset_sleep(self):
        if (self.__error == 0) and self.__pwm.is_alive():
            self.__pwm.terminate()
        self.__set_active()

    def __pwm_daemon(self, green, red):
        while True:
            GPIO.output(self.__pin, GPIO.HIGH)
            time.sleep(green)
            GPIO.output(self.__pin, GPIO.LOW)
            time.sleep(red)


if __name__ == '__main__':
    print("Use it in a proper program!")
