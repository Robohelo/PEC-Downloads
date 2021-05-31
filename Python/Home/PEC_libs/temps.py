# -*- coding: utf-8 -*-
"""
Temperature sensor lib.

Temperature sensor lib
for DS18X20 and HYT939
on the Jetson Nano.

@author: Robohelo
"""
import time
import threading
from adafruit_onewire.bus import OneWireBus
from adafruit_ds18x20 import DS18X20
from smbus2 import SMBus


class Temp():
    """
    Temperature sensor class.

    Class for temperature sensor DS18X20,
    over the DS2482-100 I2C converter chip,
    and HYT939 with humidity and tempratur
    over I2C.

    Funktions
    ----------

    get_DS18X20 :
        return : float
            in °C

    get_hyt939 :
        return : float
            in °C

    get_humidity :
        return : float
            in %RH
    """

    def __init__(self, bus=0):
        """
        Init function for tempsensors.

        Init bus 0 and the starttemps are 100°C
        same with the humidity (100%RH).

        Parameters
        ----------
        bus : int, optional
            Select the I2C bus. The default is 0.

        Returns
        -------
        None.

        """
        # start daemons
        self._DS18X20 = 100
        self._hyt939 = 100
        self._humidity = 100
        self.__shutdown_flag = False
        self.__mutex = threading.Lock()
        self.__bus = SMBus(bus)
        self.__t_DS18X20 = threading.Thread(target=self.__daemon_DS18X20)
        self.__t_hyt939 = threading.Thread(target=self.__daemon_hyt939)
        self.__t_DS18X20.start()
        self.__t_hyt939.start()

    def __daemon_DS18X20(self):
        """
        Background task.

        Daemon for DS18X20.
        Do NOT touch!

        """
        ow_bus = OneWireBus(self.__bus)
        devices = ow_bus.scan()
        ds18 = DS18X20(ow_bus, devices[0])
        errorcount = 0
        while(not self.__shutdown_flag):
            self.__mutex.acquire()
            try:
                self._DS18X20 = ds18.temperature
                errorcount = 0
            except RuntimeError:
                if errorcount > 3:
                    raise RuntimeError
                continue
                errorcount += 1
            finally:
                self.__mutex.release()
            time.sleep(30)

    def __daemon_hyt939(self):
        """
        Background task.

        Daemon for hyt939.
        Do NOT touch!

        """
        hyt939 = HYT939(self.__bus)
        while(not self.__shutdown_flag):
            self.__mutex.acquire()
            data = hyt939.get_hyt939()
            self._hyt939 = data[0]
            self._humidity = data[1]
            self.__mutex.release()
            time.sleep(1)

    def get_DS18X20(self):
        """
        DS18X20 Temp.

        Returns temperatur in °C.
        max intervall > 5 sec.

        Return
        ------
        float
            temperatur in °C.

        """
        return self._DS18X20

    def get_hyt939(self):
        """
        HYT939 Temp.

        Returns temperatur in °C.
        max intervall > 0.3 sec.

        Return
        ------
        float
            temperatur in °C.

        """
        return self._hyt939

    def get_humidity(self):
        """
        HYT939 Humidity.

        Returns humidity in %RH.
        max intervall > 0.3 sec.

        Return
        ------
        float
            humidity in %RH.

        """
        return self._humidity

    def _daemons_shutdown(self):
        """
        Kill daemons.

        For shuting down the threads.
        Should not be used careless!

        Return
        ------
        None.

        """
        self.__shutdown_flag = True
        self.__t_DS18X20.join()
        self.__t_hyt939.join()
        self._DS18X20 = 100
        self._hyt939 = 100
        self._humidity = 100


class HYT939():
    """
    Class for the HYT939 over I2C.

    Funktions
    ----------

    get_hyt939 :
        return : float
            in C°

    """

    def __init__(self, bus, addres=0x28):
        """
        Init function for the HYT939.

        Parameters
        ----------
        bus : SMBus
            SMBus object where the HYT939 is connected.
        addres : HEX, optional
            Address of the HYT939. The default is 0x28.

        Returns
        -------
        None.

        """
        self.bus = bus
        self.addres = addres

    def get_hyt939(self):
        """
        HYT939 Temp.

        Gets the temperatur and Humidity of the HYT939 over I2C.
        max frequency > 0.3 sec.

        Returns
        -------
        c_temp : TYPE
            Temperature in C°
        humidity : TYPE
            Humidity in %RH

        """
        self.bus.write_byte(self.addres, 0x80)
        time.sleep(0.3)
        # HYT939 address, 0x28(40)
        # Read data back from 0x00(00), 4 bytes
        # Humidity MSB, Humidity LSB, Temp MSB, Temp LSB
        data = self.bus.read_i2c_block_data(self.addres, 0x00, 4)
        humidity = (((data[0] & 0x3F) * 256.0) + data[1]) * (100.0 / 16383.0)
        c_temp = (((data[2] * 256.0) + (data[3] & 0xFC)) / 4) * \
            (165.0 / 16383.0) - 40
        return c_temp, humidity

if __name__ == '__main__':
    print("Debug info!")
    t = Temp()
    print("sleeping for 10s")
    time.sleep(10)
    print("DS18X20: ", end = "")
    print(t.get_DS18X20())
    print("HYT939 (temp; humidity): ", end = "")
    print(t.get_hyt939(), end = "; ")
    print(t.get_humidity())
    print("finished shutting down!")
    t._daemons_shutdown()