# Author : Ulf Lehnert (2024)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of  this software and associated documentation files (the "Software"), to
# deal in  the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copied of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
MicroPython I2C driver for MPU9250 9-axis motion tracking devices.
"""

# register addresses
_GYRO_CONFIG = const(0x1b)
_ACCEL_CONFIG = const(0x1c)
_ACCEL_CONFIG2 = const(0x1d)
_INT_PIN_CFG = const(0x37)
_ACCEL_XOUT_H = const(0x3b)
_ACCEL_XOUT_L = const(0x3c)
_ACCEL_YOUT_H = const(0x3d)
_ACCEL_YOUT_L = const(0x3e)
_ACCEL_ZOUT_H = const(0x3f)
_ACCEL_ZOUT_L= const(0x40)
_TEMP_OUT_H = const(0x41)
_TEMP_OUT_L = const(0x42)
_GYRO_XOUT_H = const(0x43)
_GYRO_XOUT_L = const(0x44)
_GYRO_YOUT_H = const(0x45)
_GYRO_YOUT_L = const(0x46)
_GYRO_ZOUT_H = const(0x47)
_GYRO_ZOUT_L = const(0x48)
_USER_CTRL = const(0x6a)
_PWR_MGMT_1 = const(0x6b)
_PWR_MGMT_2 = const(0x6c)
_WHO_AM_I = const(0x75)

# register bit masks
_I2C_BYPASS_MASK = const(0b00000010)
_I2C_BYPASS_EN = const(0b00000010)
_I2C_BYPASS_DIS = const(0b00000000)

from machine import I2C, Pin
from micropython import const
import utime
from ak8963 import AK8963

class MPU9250:
    """MicroPython I2C driver for MPU9250 9-axis motion tracking device."""
    def __init__(self, i2c:I2C, address:int=0x68):
        """
        Initialize the sensors gyro, accelerometer and magnetometer

        Args:
            i2c (I2C): bus interface
            address (int, optional): I2C bus address. Defaults to 0x68.
        """
        self.i2c = i2c
        self.address = address

        # test for presence of the IMU
        try:
            # self.whoami = self.i2c.readfrom_mem(self.address, _WHO_AM_I, 1)[0]
            self.whoami = self._read_byte_register(_WHO_AM_I)
            if self.whoami in [0x71, 0x70, 0x90]:
                # 0x70 = standalone MPU6500, 0x71 = MPU6250 SIP, 0x90 = MPU6700
                print(f'MPU with ID {hex(self.whoami)} found at address {hex(self.address)}')
            else:
                raise RuntimeError('Invalid ID of MPU-9250 : {hex(self.whoami)}')
        except:
            raise RuntimeError(f'Bus error when reading from I2C0 bus address {hex(self.address)} register {hex(_WHO_AM_I)}.')

        # self.i2c.writeto_mem(self.address, _PWR_MGMT_1, bytes([0x80])) # reset
        try:
            self._write_byte_register(_PWR_MGMT_1, bytes([0x80])) # reset
            utime.sleep_ms(100)
            self._write_byte_register(_PWR_MGMT_1, bytes([0x00])) # disable sleep mode, internal 8MHz oscillator
            self._write_byte_register(_PWR_MGMT_2, bytes([0x00])) # disable standby modes
            utime.sleep_ms(100)
        except:
            raise RuntimeError(f'I2C bus error during MPU-9250 reset.')
        
        """
        try:
            # configure I2C bus pass-through to access AK8963 directly.
            reg = self._read_byte_register(_INT_PIN_CFG)
            reg &= ~_I2C_BYPASS_MASK
            reg |= _I2C_BYPASS_EN
            self._write_byte_register(_INT_PIN_CFG, bytes([reg]))
        except:
            raise RuntimeError(f'I2C bus when configuring MPU-9250 bus pass-through.')
        utime.sleep_ms(10)
        """
        # self.ak8963 = AK8963(self.i2c)

        # configure IMU

    def _read_byte_register(self, register:int) -> int:
        """
        Read a register over the I2C bus.

        Args:
            register (int): register address (8-bit)

        Returns:
            int: value (8-bit)
        """
        return self.i2c.readfrom_mem(self.address, register, 1)[0]
    
    def _write_byte_register(self, register:int, values:bytes) -> None:
        """
        Write registers ober the I2C bus.

        Args:
            register (int): register address (8-bit)
            value (bytes): values to be written
        """
        print(f'writing {values} to I2C addres {hex(self.address)} reg {hex(register)}')
        self.i2c.writeto_mem(self.address, register, values)