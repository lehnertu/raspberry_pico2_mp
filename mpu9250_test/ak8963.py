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
MicroPython I2C driver for AK8963 3-axis magnetometer devices.
"""

# register addresses
_WHO_AM_I = const(0x00)

# register bit masks

from machine import I2C, Pin
from micropython import const
import utime

class AK8963:
    """MicroPython I2C driver for AK8963 3-axis magnetometer devices."""
    def __init__(self, i2c, address=0x0c):
        """
        Initialize the sensor.

        Args:
            i2c (I2C): bus interface
            address (hint, optional): I2C bus address. Defaults to 0x0c.
        """
        self.i2c = i2c
        self.address = address

        # test for presence of the IMU
        try:
            # self.whoami = self.i2c.readfrom_mem(self.address, _WHO_AM_I, 1)[0]
            self.whoami = self._read_byte_register(_WHO_AM_I)
            if 0x48 == self.whoami:
                print(f'AK8963 with ID {hex(self.whoami)} found at address {hex(self.address)}')
            else:
                raise RuntimeError('Invalid ID of AK8963 : {hex(self.whoami)}')
        except:
            raise RuntimeError(f'Bus error when reading from I2C0 bus address {hex(self.address)} register {hex(_WHO_AM_I)}.')

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
        self.i2c.writeto_mem(self.address, register, values)