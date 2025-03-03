# 
# Convenience class for devices connected via an I2C bus
# for Micro-Python
#
# @author Ulf Lehnert
# @date 03.02.2025
# 

from machine import I2C

class I2C_Device:
    """
    utility class for I2C driven sensors
    """
    def __init__(self, i2c:I2C, address:int, debug:bool=False):
        """
        Set the bus parameters.
        Args:
            i2c (I2C): bus interface
            address (int): I2C bus address.
            debug(bool, optional): whether to print debug output. Default False
        TODO: sanity check
        """
        self.i2c = i2c
        self.address = address
        self.debug = debug
        if debug:
            print('I2C bus scan: ', i2c.scan())

    def read_byte_register(self, register:int) -> int:
        """
        Read a register over the I2C bus.

        Args:
            register (int): register address (8-bit)

        Returns:
            int: value (8-bit)
        """
        return self.i2c.readfrom_mem(self.address, register, 1)[0]
    
    def read_into_buffer(self, register:int, buf:bytes) -> None:
        """
        Read bytes into *buf* starting from the a register address *register*.
        The number of bytes read is defined by the size of *buf*.

        Args:
            register (int): start address (8-bit)
            buf (bytes): buffer to be filled
        """
        self.i2c.readfrom_mem_into(self.address, register, buf)

    def write_byte_register(self, register:int, values:bytes) -> None:
        """
        Write registers on the I2C device.

        Args:
            register (int): register address (8-bit)
            value (bytes): values to be written
        """
        if self.debug:
            print(f'writing 0x{values.hex()} to I2C addres {self.address:#04x} reg {register:#04x}')
        self.i2c.writeto_mem(self.address, register, values)

class I2C_ByteRegister_RW:
    """
    Class for read/write byte register on an I2C device.
    """
    def __init__(self, register:int) -> None:
        """
        define a register on a device.

        Args:
            register (int): register address
        """
        self._register = register
    
    def __get__(self, instance, owner) -> int:
        """
        read and return return the value read from the register on the I2C device
        """
        return instance.read_byte_register(self._register)

    def __set__(self, instance, value:int) -> None:
        """
        this writes the register over the I2C bus.

        Args:
            value (int): register content to be written
        """
        instance.write_byte_register(self._register,bytes([value]))

class I2C_ByteRegister_WO:
    """
    Class for write-only byte register on an I2C device.
    A read only returns a cached value from the last write.
    This is for speed-up by avoiding unnecessary reads.
    """
    def __init__(self, register:int) -> None:
        """
        define a register on a device.

        Args:
            device (I2C_Device): the device
            register (int): register address
        """
        self._register = register
        self._value = None
    
    def __get__(self, instance, owner):
        """
        return the cached value or throw an exception if no write has occured yet
        """
        if self._value is None:
            raise RuntimeError(f'Value of I2C_ByteRegister_WO({self._register:#04x}) has never been assigned')
        return self._value

    def __set__(self, instance, value:int) -> None:
        """
        this writes the register over the I2C bus.

        Args:
            value (int): register content to be written
        """
        self._value = value
        instance.write_byte_register(self._register,bytes([value]))