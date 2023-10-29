import network
import socket
import machine
import time
import math
import urequests
import json
from ustruct import unpack, unpack_from
from array import array
from micropython import const
from utime import sleep_ms


BME280_I2CADDR = 0x76

BME280_OSAMPLE_1 = 1
BME280_OSAMPLE_2 = 2
BME280_OSAMPLE_4 = 3
BME280_OSAMPLE_8 = 4
BME280_OSAMPLE_16 = 5

BME280_REGISTER_CONTROL_HUM = 0xF2
BME280_REGISTER_STATUS = 0xF3
BME280_REGISTER_CONTROL = 0xF4

MODE_SLEEP = const(0)
MODE_FORCED = const(1)
MODE_NORMAL = const(3)

BME280_TIMEOUT = const(100)


class BH1750:
    MEASUREMENT_MODE_CONTINUOUSLY = const(1)
    MEASUREMENT_MODE_ONE_TIME = const(2)
    
    RESOLUTION_HIGH = const(0)
    RESOLUTION_HIGH_2 = const(1)
    RESOLUTION_LOW = const(2)
    
    MEASUREMENT_TIME_DEFAULT = const(69)
    MEASUREMENT_TIME_MIN = const(31)
    MEASUREMENT_TIME_MAX = const(254)

    def __init__(self, address, i2c):
        self._address = address
        self._i2c = i2c
        self._measurement_mode = BH1750.MEASUREMENT_MODE_ONE_TIME
        self._resolution = BH1750.RESOLUTION_HIGH
        self._measurement_time = BH1750.MEASUREMENT_TIME_DEFAULT
        
        self._write_measurement_time()
        self._write_measurement_mode()
        
    def configure(self, measurement_mode: int, resolution: int, measurement_time: int):
        if measurement_time not in range(BH1750.MEASUREMENT_TIME_MIN, BH1750.MEASUREMENT_TIME_MAX + 1):
            raise ValueError("measurement_time must be between {0} and {1}"
                             .format(BH1750.MEASUREMENT_TIME_MIN, BH1750.MEASUREMENT_TIME_MAX))
        
        self._measurement_mode = measurement_mode
        self._resolution = resolution
        self._measurement_time = measurement_time
        
        self._write_measurement_time()
        self._write_measurement_mode()
    
    def _write_measurement_time(self):
        buffer = bytearray(1)
        
        high_bit = 1 << 6 | self._measurement_time >> 5
        low_bit = 3 << 5 | (self._measurement_time << 3) >> 3
                
        buffer[0] = high_bit
        self._i2c.writeto(self._address, buffer)
        
        buffer[0] = low_bit
        self._i2c.writeto(self._address, buffer)
        
    def _write_measurement_mode(self):
        buffer = bytearray(1)
                
        buffer[0] = self._measurement_mode << 4 | self._resolution
        self._i2c.writeto(self._address, buffer)
        sleep_ms(24 if self._measurement_time == BH1750.RESOLUTION_LOW else 180)
        
    def reset(self):
        self._i2c.writeto(self._address, bytearray(b'\x07'))
    
    def power_on(self):
        self._i2c.writeto(self._address, bytearray(b'\x01'))

    def power_off(self):
        self._i2c.writeto(self._address, bytearray(b'\x00'))

    @property
    def measurement(self) -> float:
        if self._measurement_mode == BH1750.MEASUREMENT_MODE_ONE_TIME:
            self._write_measurement_mode()
            
        buffer = bytearray(2)
        self._i2c.readfrom_into(self._address, buffer)
        lux = (buffer[0] << 8 | buffer[1]) / (1.2 * (BH1750.MEASUREMENT_TIME_DEFAULT / self._measurement_time))
        
        if self._resolution == BH1750.RESOLUTION_HIGH_2:
            return lux / 2
        else:
            return lux
    
    def measurements(self) -> float:
        while True:
            yield self.measurement
            
            if self._measurement_mode == BH1750.MEASUREMENT_MODE_CONTINUOUSLY:
                base_measurement_time = 16 if self._measurement_time == BH1750.RESOLUTION_LOW else 120
                sleep_ms(math.ceil(base_measurement_time * self._measurement_time / BH1750.MEASUREMENT_TIME_DEFAULT))


class BME280:

    def __init__(self,
                 mode=BME280_OSAMPLE_8,
                 address=BME280_I2CADDR,
                 i2c=None,
                 **kwargs):

        if type(mode) is tuple and len(mode) == 3:
            self._mode_hum, self._mode_temp, self._mode_press = mode
        elif type(mode) == int:
            self._mode_hum, self._mode_temp, self._mode_press = mode, mode, mode
        else:
            raise ValueError("Wrong type for the mode parameter, must be int or a 3 element tuple")

        for mode in (self._mode_hum, self._mode_temp, self._mode_press):
            if mode not in [BME280_OSAMPLE_1, BME280_OSAMPLE_2, BME280_OSAMPLE_4,
                            BME280_OSAMPLE_8, BME280_OSAMPLE_16]:
                raise ValueError(
                    'Unexpected mode value {0}. Set mode to one of '
                    'BME280_ULTRALOWPOWER, BME280_STANDARD, BME280_HIGHRES, or '
                    'BME280_ULTRAHIGHRES'.format(mode))

        self.address = address
        if i2c is None:
            raise ValueError('An I2C object is required.')
        self.i2c = i2c
        self.__sealevel = 101325

        dig_88_a1 = self.i2c.readfrom_mem(self.address, 0x88, 26)
        dig_e1_e7 = self.i2c.readfrom_mem(self.address, 0xE1, 7)
        self.dig_T1, self.dig_T2, self.dig_T3, self.dig_P1, \
            self.dig_P2, self.dig_P3, self.dig_P4, self.dig_P5, \
            self.dig_P6, self.dig_P7, self.dig_P8, self.dig_P9, \
            _, self.dig_H1 = unpack("<HhhHhhhhhhhhBB", dig_88_a1)

        self.dig_H2, self.dig_H3, self.dig_H4,\
            self.dig_H5, self.dig_H6 = unpack("<hBbhb", dig_e1_e7)
        self.dig_H4 = (self.dig_H4 * 16) + (self.dig_H5 & 0xF)
        self.dig_H5 //= 16

        self.t_fine = 0

        self._l1_barray = bytearray(1)
        self._l8_barray = bytearray(8)
        self._l3_resultarray = array("i", [0, 0, 0])

        self._l1_barray[0] = self._mode_temp << 5 | self._mode_press << 2 | MODE_SLEEP
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL,
                             bytearray([0x3c | MODE_SLEEP]))

    def read_raw_data(self, result):

        self._l1_barray[0] = self._mode_hum
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL_HUM,
                             self._l1_barray)
        self._l1_barray[0] = self._mode_temp << 5 | self._mode_press << 2 | MODE_FORCED
        self.i2c.writeto_mem(self.address, BME280_REGISTER_CONTROL,
                             self._l1_barray)

        for _ in range(BME280_TIMEOUT):
            if self.i2c.readfrom_mem(self.address, BME280_REGISTER_STATUS, 1)[0] & 0x08:
                time.sleep_ms(10)
            else:
                break
        else:
            raise RuntimeError("Sensor BME280 not ready")

        self.i2c.readfrom_mem_into(self.address, 0xF7, self._l8_barray)
        readout = self._l8_barray
        raw_press = ((readout[0] << 16) | (readout[1] << 8) | readout[2]) >> 4
        raw_temp = ((readout[3] << 16) | (readout[4] << 8) | readout[5]) >> 4
        raw_hum = (readout[6] << 8) | readout[7]

        result[0] = raw_temp
        result[1] = raw_press
        result[2] = raw_hum

    def read_compensated_data(self, result=None):
        self.read_raw_data(self._l3_resultarray)
        raw_temp, raw_press, raw_hum = self._l3_resultarray

        var1 = (((raw_temp // 8) - (self.dig_T1 * 2)) * self.dig_T2) // 2048
        var2 = (raw_temp // 16) - self.dig_T1
        var2 = (((var2 * var2) // 4096) * self.dig_T3) // 16384
        self.t_fine = var1 + var2
        temp = (self.t_fine * 5 + 128) // 256

        var1 = self.t_fine - 128000
        var2 = var1 * var1 * self.dig_P6
        var2 = var2 + ((var1 * self.dig_P5) << 17)
        var2 = var2 + (self.dig_P4 << 35)
        var1 = (((var1 * var1 * self.dig_P3) >> 8) +
                ((var1 * self.dig_P2) << 12))
        var1 = (((1 << 47) + var1) * self.dig_P1) >> 33
        if var1 == 0:
            pressure = 0
        else:
            p = ((((1048576 - raw_press) << 31) - var2) * 3125) // var1
            var1 = (self.dig_P9 * (p >> 13) * (p >> 13)) >> 25
            var2 = (self.dig_P8 * p) >> 19
            pressure = ((p + var1 + var2) >> 8) + (self.dig_P7 << 4)

        h = self.t_fine - 76800
        h = (((((raw_hum << 14) - (self.dig_H4 << 20) -
                (self.dig_H5 * h)) + 16384) >> 15) *
             (((((((h * self.dig_H6) >> 10) *
                (((h * self.dig_H3) >> 11) + 32768)) >> 10) + 2097152) *
              self.dig_H2 + 8192) >> 14))
        h = h - (((((h >> 15) * (h >> 15)) >> 7) * self.dig_H1) >> 4)
        h = 0 if h < 0 else h
        h = 419430400 if h > 419430400 else h
        humidity = h >> 12

        if result:
            result[0] = temp
            result[1] = pressure
            result[2] = humidity
            return result

        return array("i", (temp, pressure, humidity))

    @property
    def sealevel(self):
        return self.__sealevel

    @sealevel.setter
    def sealevel(self, value):
        if 300 < value < 1200:
            self.__sealevel = value

    @property
    def altitude(self):
        from math import pow
        try:
            p = 44330 * (1.0 - pow((self.read_compensated_data()[1] / 256) /
                                   self.__sealevel, 0.1903))
        except:
            p = 0.0
        return p

    @property
    def dew_point(self):
        from math import log
        t, p, h = self.read_compensated_data()
        t /= 100
        h /= 1024
        h = (log(h, 10) - 2) / 0.4343 + (17.62 * t) / (243.12 + t)
        return (243.12 * h / (17.62 - h)) * 100

    @property
    def values(self):

        t, p, h = self.read_compensated_data()

        p = p / 256

        h = h / 1024
        return ("{}C".format(t / 100), "{:.02f}hPa".format(p/100),
                "{:.02f}%".format(h))


class TCPServer:

    def __init__(self):
        self.ssid = "UPC3739675"
        self.password = "Zz3dvtzkhxw7"
        self.sta_if = self.setup_network()
        self.server = self.setup_socket()

    def __del__(self):
        pass

    def setup_network(self):
        sta_if = network.WLAN(network.STA_IF)
        sta_if.active(True)
        sta_if.connect(self.ssid, self.password)
        while not sta_if.isconnected():
            pass
        self.ip = sta_if.ifconfig()[0]
        return sta_if

    def setup_socket(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        server_ip = "0.0.0.0"
        server_port = 8080
        server_socket.bind((server_ip, server_port))

        server_socket.listen(1)
        return server_socket
    
    def handle_connections(self):
        client_socket, client_address = self.server.accept()
        data = client_socket.recv(1024).decode("utf-8")

        if data:
            self.handle_response(True, client_socket)
        else:
            self.handle_response(False, client_socket)

        client_socket.close()
        return client_address, data

    def handle_response(self, recieved_data, client_socket):
        if recieved_data:
            client_socket.send('HTTP/1.1 200 OK\n')
            client_socket.send('Content-Type: text/html\n')
            client_socket.send('Connection: close\n\n')
        else:
            client_socket.send('HTTP/1.1 400 Error\n')
            client_socket.send('Content-Type: text/html\n')
            client_socket.send('Connection: close\n\n')


class SendData:
    
    def __init__(self, address, subaddress, data):
        self.uri = address + subaddress
        self.data = data

    def __del__(self):
        pass

    def post(self):
        response = urequests.request('POST', url=self.uri, json=self.data)
        if 200 in response:
            return True
        else:
            return False

def main():
    address = "https://192.168.0.101:51630"

    tcp = TCPServer()
    i2c = machine.SoftI2C(scl=machine.Pin(22), sda=machine.Pin(21))
    bme = BME280(address=0x76, i2c=i2c)
    bh1750 = BH1750(0x23, i2c)

    while True:

        tcp.handle_connections()
        bme_data = bme.read_compensated_data()

        measurements = {
            "light": bh1750.measurement,
            "temperature": bme_data[0],
            "pressure": bme_data[1],
            "humidity": bme_data[2],
        }

        send_data = SendData(address, "/api/sensor", measurements)
        send_data.post()

main()