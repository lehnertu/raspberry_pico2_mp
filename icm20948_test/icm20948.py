# 
# Library for the ST ICM-20948 9-DoF Accel/Gyro/Mag sensor
# for Micro-Python using I2C bus 
#
# @author Ulf Lehnert
# @date 01.02.2025
# 
# with information from https://github.com/adafruit/Adafruit_CircuitPython_ICM20X.git
# and https://github.com/pimoroni/icm20948-python.git
#

from machine import I2C
from i2c_device import I2C_Device, I2C_ByteRegister_RW, I2C_ByteRegister_WO
from micropython import const
import utime
import struct

_ICM20948_DEFAULT_ADDRESS = const(0x69)  # default i2c address
_ICM20948_DEVICE_ID = const(0xEA)  # expected content of WHO_AM_I register

class AccelConfig(dict):
    """
    class for the configuration of the accelerometer.
    provides default values and sanity checks of parameters.
    """
    CONFIG_SCALE = {'2g':0x00, '4g':0x02, '8g':0x04, '16g':0x06}
    CONFIG_DLPF = {'off':0x00, '246Hz':0x01, '111.4Hz':0x11, '50.4Hz':0x19,
                   '23.9Hz':0x21, '11.5Hz':0x29, '5.7Hz':0x31, '473HZ':0x39}
    DEFAULTS = {'SampleRateDiv':0, 'FullScale':'16g', 'LowPass':'Off'}

    def __init__(self, initial_values=None) -> None:
        super().__init__(self.DEFAULTS)
        if initial_values:
            for key, value in initial_values.items():
                self.__setitem__(key,value)

    def __setitem__(self, key, value):
        if key=='SampleRateDiv':
            if value<0 or value>4095:
                raise ValueError('AccelConfig : illegal FSampleRateDiv value')
        if key=='FullScale':
            if value not in self.CONFIG_SCALE.keys():
                raise ValueError('AccelConfig : illegal FullScale value')
        if key=='LowPass':
            if value not in self.CONFIG_DLPF.keys():
                raise ValueError('AccelConfig : illegal LowPass value')
        super().__setitem__(key, value)

class GyroConfig(dict):
    """
    class for the configuration of the gyro.
    provides default values and sanity checks of parameters.
    """
    CONFIG_SCALE = {'250dps':0x00, '500dps':0x02, '1000dps':0x04, '2000dps':0x06}
    CONFIG_DLPF = {'off':0x00, '196.6Hz':0x01, '151.8Hz':0x09, '119.5Hz':0x11, '51.2Hz':0x19,
                   '23.9Hz':0x21, '11.6Hz':0x29, '5.7Hz':0x31, '361.4HZ':0x39}
    DEFAULTS = {'SampleRateDiv':0, 'FullScale':'2000dps', 'LowPass':'Off'}

    def __init__(self, initial_values=None) -> None:
        super().__init__(self.DEFAULTS)
        if initial_values:
            for key, value in initial_values.items():
                self.__setitem__(key,value)

    def __setitem__(self, key, value):
        if key=='SampleRateDiv':
            if value<0 or value>0xff:
                raise ValueError('GyroConfig : illegal FSampleRateDiv value')
        if key=='FullScale':
            if value not in self.CONFIG_SCALE.keys():
                raise ValueError('GyroConfig : illegal FullScale value')
        if key=='LowPass':
            if value not in self.CONFIG_DLPF.keys():
                raise ValueError('GyroConfig : illegal LowPass value')
        super().__setitem__(key, value)

class ICM20948(I2C_Device):
    """
    """

    # all banks
    ICM20948_BANK_SEL = I2C_ByteRegister_WO(0x7F)

    # bank 0
    WHO_AM_I = I2C_ByteRegister_RW(0x00)
    USER_CTRL = I2C_ByteRegister_RW(0x03)
    LP_CONFIG = I2C_ByteRegister_RW(0x05)
    PWR_MGMT_1 = I2C_ByteRegister_RW(0x06)
    PWR_MGMT_2 = I2C_ByteRegister_RW(0x07)
    INT_PIN_CFG = I2C_ByteRegister_RW(0x0f)
    ACCEL_XOUT_H = const(0x2d)
    GYRO_XOUT_H = const(0x33)
    TEMP_OUT_H = const(0x39)

    # bank 1

    # bank 2
    GYRO_SMPLRT_DIV = I2C_ByteRegister_RW(0x00)
    GYRO_CONFIG_1 = I2C_ByteRegister_RW(0x01)
    GYRO_CONFIG_2 = I2C_ByteRegister_RW(0x02)
    ACCEL_SMPLRT_DIV_1 = I2C_ByteRegister_RW(0x10)
    ACCEL_SMPLRT_DIV_2 = I2C_ByteRegister_RW(0x11)
    ACCEL_CONFIG = I2C_ByteRegister_RW(0x14)
    
    # bank 3

    def __init__(self, i2c:I2C, address:int=_ICM20948_DEFAULT_ADDRESS, debug:bool=False) -> None:
        """
        Initialize the sensors gyro, accelerometer and gaussmeter

        default accelerometer configuration
        - SampleRateDiv = 3 - 375 Hz
        - FullScale = 4g
        - LPF = 

        Args:
            i2c (I2C): bus interface
            address (int, optional): I2C bus address. Defaults to 0x69.
            debug(bool, optional): whether to print debug output. Default False
        """
        super().__init__(i2c, address)
        self.debug = debug

        # fixed memory blocks prevent allocations at runtime
        # we have a single memory buffer for all motion data
        # there exists references (views) of the acceleration or motion data separately
        # but these access the same memory buffer
        self.acc_gyro_buf = bytearray(12)
        self.acc_buf = memoryview(self.acc_gyro_buf)[:6]
        self.gyro_buf = memoryview(self.acc_gyro_buf)[6:]
        self.temp_buf = bytearray(2)

        # test for presence of the IMU
        self._bank = 0
        try:
            test = self.WHO_AM_I
            if test == _ICM20948_DEVICE_ID:
                if self.debug:
                    print(f'MPU ICM-20948 with ID {test:#04x} found at address {self.address:#04x}')
            else:
                raise RuntimeError(f'Invalid ID of ICM-20948 : {test:#04x}')
        except:
            raise RuntimeError(f'Bus error when reading from I2C bus address {self.address:#04x}.')

        # reset
        utime.sleep_ms(10)
        self.PWR_MGMT_1 = 0x80
        utime.sleep_ms(10)
        # wait for the reset bit to clear
        while self.PWR_MGMT_1 & 0x80:
            utime.sleep_ms(10)
        # enable clock, wake up from sleep
        self.PWR_MGMT_1 = 0x01
        # enable all acc and gyro axes
        self.PWR_MGMT_2 = 0x00
        # enable duty-cycled mode, data rate is set by registers
        self.LP_CONFIG = 0x40

        # SampleRateDiv=2 : 375 Hz
        self.accConfig = AccelConfig({'SampleRateDiv':2, 'FullScale':'4g', 'LowPass':'111.4Hz'})
        print(self.accConfig)
        self.configureAccel(self.accConfig)

        # SampleRateDiv=2 : 375 Hz
        self.gyrConfig = GyroConfig({'SampleRateDiv':2, 'FullScale':'500dps', 'LowPass':'119.5Hz'})
        print(self.gyrConfig)
        self.configureGyro(self.gyrConfig)

        # configure interrupt pin as active-high latched mode
        self._bank = 0
        self.INT_PIN_CFG = 0x30

        """ more necessary (?) initializations

                # reset and enable DMP and I2C-master functionalite
                USER_CTRL

                self.bank(3)
                self.write(ICM20948_I2C_MST_CTRL, 0x4D)
                self.write(ICM20948_I2C_MST_DELAY_CTRL, 0x01)

                if not self.mag_read(AK09916_WIA) == AK09916_CHIP_ID:
                    raise RuntimeError("Unable to find AK09916")

                # Reset the magnetometer
                self.mag_write(AK09916_CNTL3, 0x01)
                while self.mag_read(AK09916_CNTL3) == 0x01:
                    time.sleep(0.0001)
        """

    @property
    def _bank(self) -> int:
        """
        read the bank register

        Returns:
            int: bank
        """
        return self.ICM20948_BANK_SEL >> 4

    @_bank.setter
    def _bank(self, value: int) -> None:
        """
        Switch bank.
        The actual register write is only performed, if the requested bank differs from the current.
        
        Args:
            value (int): bank

        Raises:
            RuntimeError: if non-existent bank is requested
        """
        if value<0 or value>3:
            raise RuntimeError(f'illegal register bank {value} requested.')
        self.ICM20948_BANK_SEL = value << 4

    def configureAccel(self, config:AccelConfig) -> None:
        """
        Configure the acquisition parameters of the accelerometer.
        A sanity check of the values is done when creating the config.

        configured parameters:
        - SampleRateDiv : output sample rate is computed as 1.125 kHz/(1+SampleRateDiv)
        - FullScale : sensor range
        - LowPass : digital low-pass filtering

        Args:
            config (AccelConfig): configuration dictionary
        """
        self._bank = 2
        # ACCEL_SMPLRT_DIV_1/ACCEL_SMPLRT_DIV_2 forming a 12-bit register
        reg = (config['SampleRateDiv'] >> 8) & 0x0f
        if self.debug:
            print(f'setting ACCEL_SMPLRT_DIV_1 as {reg:#04x}')
        self.ACCEL_SMPLRT_DIV_1 = reg
        reg = config['SampleRateDiv'] & 0xff
        if self.debug:
            print(f'setting ACCEL_SMPLRT_DIV_2 as {reg:#04x}')
        self.ACCEL_SMPLRT_DIV_2 = reg
        # LPF and FullScale Setting ar in ACCEL_CONFIG
        reg = AccelConfig.CONFIG_DLPF[config['LowPass']] | AccelConfig.CONFIG_SCALE[config['FullScale']]
        if self.debug:
            print(f'setting ACCEL_CONFIG as {reg:#04x}')
        self.ACCEL_CONFIG = reg
        # determine the scaling factor
        if config['FullScale'] == '2g':
            self.acc_scale = 2.0/32768.0
        elif config['FullScale'] == '4g':
            self.acc_scale = 4.0/32768.0
        elif config['FullScale'] == '8g':
            self.acc_scale = 8.0/32768.0
        else:
            self.acc_scale = 16.0/32768.0

    def configureGyro(self, config:GyroConfig) -> None:
        """
        Configure the acquisition parameters of the gyroscope.
        A sanity check of the values is done when creating the config.

        configured parameters:
        - SampleRateDiv : output sample rate is computed as 1.125 kHz/(1+SampleRateDiv)
        - FullScale : sensor range
        - LowPass : digital low-pass filtering

        Args:
            config (GyroConfig): configuration dictionary
        """
        self._bank = 2
        reg = config['SampleRateDiv'] & 0xff
        if self.debug:
            print(f'setting GYRO_SMPLRT_DIV as {reg:#04x}')
        self.GYRO_SMPLRT_DIV = reg
        # LPF and FullScale Setting ar in GYRO_CONFIG_1
        # read and keep bits that we don't want to change - not neccessary, reserved bits are 0 
        reg = self.GYRO_CONFIG_1 & 0b11000000
        reg |= GyroConfig.CONFIG_DLPF[config['LowPass']]
        reg |= GyroConfig.CONFIG_SCALE[config['FullScale']]
        if self.debug:
            print(f'setting GYRO_CONFIG_1 as {reg:#04x}')
        self.GYRO_CONFIG_1 = reg
        # self-test and averaging in low-power mode - should not be neccessary
        self.GYRO_CONFIG_2 = 0x00
        # determine the scaling factor
        if config['FullScale'] == '250dps':
            self.gyro_scale = 250.0/32768.0
        elif config['FullScale'] == '500dps':
            self.gyro_scale = 500.0/32768.0
        elif config['FullScale'] == '1000dps':
            self.gyro_scale = 1000.0/32768.0
        else:
            self.gyro_scale = 2000.0/32768.0

    def read_AccelGyro(self) -> None:
        """
        Read 12 bytes of raw motion data (accelerometer and gyro)
        into the pre-allocated buffer.
        """
        # avoid unnecessary writes of the bank register by reading the cached value first
        if not self._bank == 0: self._bank=0
        # read a block of registers at once
        self.read_into_buffer(self.ACCEL_XOUT_H, self.acc_gyro_buf)

    def read_Accel(self) -> None:
        """
        Read 6 bytes of raw motion data from accelerometer
        into the pre-allocated buffer.
        """
        # avoid unnecessary writes of the bank register by reading the cached value first
        if not self._bank == 0: self._bank=0
        # read a block of registers at once
        self.read_into_buffer(self.ACCEL_XOUT_H, self.acc_buf)

    def read_Gyro(self) -> None:
        """
        Read 6 bytes of raw motion data from gyroscope
        into the pre-allocated buffer.
        """
        # avoid unnecessary writes of the bank register by reading the cached value first
        if not self._bank == 0: self._bank=0
        # read a block of registers at once
        self.read_into_buffer(self.GYRO_XOUT_H, self.acc_buf)

    def read_Temp(self) -> None:
        """
        Read 2 bytes of temperature
        into the pre-allocated buffer.
        """
        # avoid unnecessary writes of the bank register by reading the cached value first
        if not self._bank == 0: self._bank=0
        # read a block of registers at once
        self.read_into_buffer(self.TEMP_OUT_H, self.temp_buf)

    def get_accel(self):
        """
        After reading the raw data, use this to report a scaled measurement in [g].
        Returns a list of 3 floats.
        """
        data = struct.unpack(">hhh", self.acc_buf)
        scaled_values = [x * self.acc_scale for x in data]
        return scaled_values
    
    def get_gyro(self):
        """
        After reading the raw data, use this to report a scaled measurement in [dps].
        Returns a list of 3 floats.
        """
        data = struct.unpack(">hhh", self.gyro_buf)
        scaled_values = [x * self.gyro_scale for x in data]
        return scaled_values