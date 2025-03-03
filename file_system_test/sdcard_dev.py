"""
MicroPython driver for SD cards using SPI bus.

for further information see: http://elm-chan.org/docs/mmc/mmc_e.html

Requires an SPI bus and a CS pin.  Provides readblocks and writeblocks
methods so the device can be mounted as a filesystem.

Example usage on pyboard:

    import pyb, sdcard, os
    sd = sdcard.SDCard(pyb.SPI(1), pyb.Pin.board.X5)
    sd.init_card()
    pyb.mount(sd, '/sd2')
    os.listdir('/')

Example usage on ESP8266:

    import machine, sdcard, os
    sd = sdcard.SDCard(machine.SPI(1), machine.Pin(15))
    sd.init_card()
    os.mount(sd, '/sd')
    os.listdir('/')

"""

from micropython import const
from machine import SPI, Pin
import time

# R1 command responses
_R1_IDLE_STATE = const(1 << 0)
_R1_ERASE_RESET = const(1 << 1)
_R1_ILLEGAL_COMMAND = const(1 << 2)
_R1_COM_CRC_ERROR = const(1 << 3)
_R1_ERASE_SEQUENCE_ERROR = const(1 << 4)
_R1_ADDRESS_ERROR = const(1 << 5)
_R1_PARAMETER_ERROR = const(1 << 6)

_TOKEN_CMD25 = const(0xFC)
_TOKEN_STOP_TRAN = const(0xFD)
_TOKEN_DATA = const(0xFE)

class SDCard:
    """
    Representation of an SD card accessed via SPI bus.
    The object can be used as a regular block device.
    It provides readblocks(), writeblocks() and ioctl(op) with opcodes 4 and 5.
    After creating the object init_card() must be called separately, when the card is present.

    internal variables :
        spi (SPI): bus interface
        cs (Pin): the pin used to drive the chip-select signal of the card
        baudrate (int): bus frequency - defaults to 1 MHz
        cmdbuf (6 bytes) : buffer for commands to be sent to the card
        block (512 bytes) : buffer for data blocks
        block_memoryview : a memory view of block that allows slicing without creating copies
        tokenbuf (1 byte) : buffer for tokens returned by card commands
        ocr (4 bytes) : operation conditions register (read by CMD 58)
        csd (16 bytes) : card specific data (read by CMD 9)
        cid (16 bytes) : card identification (read by CMD 10)
        sectors (int) : capacity of the card in 512-byte sectors
    """
    def __init__(self, spi: SPI, cs: Pin, baudrate:int=25_000_000, debug_level:int=0) -> None:
        """
        Object initialization.
        This does not access the card in any way, only creates the object.
        Card initialization must be done explicitly using init_card().

        Args:
            spi (SPI): bus interface
            cs (Pin): the pin used to drive the chip-select signal of the card
            baudrate (int): bus frequency - defaults to 25 MHz
            debug_level (int): level of verbosity
                0: (default) no printout at all
                1: print top-level call parameters
                2: print all commands executed on the card
        """
        self.spi = spi
        self.cs = cs
        self.baudrate = baudrate
        self.debug_level = debug_level
        self.cmdbuf = bytearray(6)
        self.block = bytearray(512)
        self.tokenbuf = bytearray(1)
        for i in range(512):
            self.block[i] = 0xFF
        self.block_memoryview = memoryview(self.block)
        self.ocr = bytearray(4)
        self.csd = bytearray(16)
        self.cid = bytearray(16)
        self.sectors = 0

    def init_spi(self, freq:int) -> None:
        """
        initialize the SPI bus

        Args:
            freq (int): bus transfer frequency
        """
        self.spi.init(baudrate=freq, phase=0, polarity=0)

    def power_up_sequence(self):
        """
        Power up initialization of the card
        """
        # init CS pin and deselect
        self.cs.init(self.cs.OUT, value=1)
        time.sleep_ms(10)
        # init SPI bus; use low data rate for initialisation
        self.init_spi(100000)
        # clock card at least 74 cycles (here 80) with cs high
        for i in range(10):
            self.spi.write(b"\xff")

    def cmd(self, cmd:int, arg:int, crc:int) -> int:
        """
        Execute a command on the SD card expecting an R1 response.

        The command is assembled with twwo fixed bits (0,1) and the command number as first byte,
        followed by the argument and the CRC check sum which must have the least significant bit set to 1.
        This buffer ist shifted out to the card. After that we wait for a response from the card
        by trying to read one byte while keeping MOSI=1 (writing 0xff).
        A valid response is assumed if we get a value with MSB=0. (Before the card has processed the command
        we typically get 0xff). This response value is returned.
        The CS signal is released afterwards.

        Args:
            cmd (int): Command number (6-bit)
            arg (int): 32-bit arguments for the command
            crc (int): 7-bit check sum + LSB=1

        Returns:
            (int): the response value
        """
        if self.debug_level >= 2:
            print(f'[SDCard] CMD={cmd} ARG={arg} CRC={crc}')
        self.cs(0)
        # create and send the command
        buf = self.cmdbuf
        buf[0] = 0x40 | cmd
        buf[1] = arg >> 24
        buf[2] = arg >> 16
        buf[3] = arg >> 8
        buf[4] = arg
        buf[5] = crc
        self.spi.write(buf)
        # wait for the response (response[7] == 0)
        # try at maximum 10 times
        for i in range(10):
            self.spi.readinto(self.tokenbuf, 0xFF)
            response = self.tokenbuf[0]
            if not (response & 0x80):
                # normal return
                if self.debug_level >= 2:
                    print(f'[SDCard] CMD({cmd}) response {response}')
                # release bus
                self.cs(1)
                self.spi.write(b"\xff")
                return response
        # timeout
        if self.debug_level >= 1:
            print(f'[SDCard] CMD({cmd}) timeout!')
        self.cs(1)
        self.spi.write(b"\xff")
        return -1
        
    def cmd_buf(self, cmd:int, arg:int, crc:int, buffer:bytes) -> int:
        """
        Execute a command on the SD card expecting an R1 response plus some data.
        Size of the data block is given by the size of the buffer.
        The CS signal is released after reading the R1 response and filling the buffer.

        Args:
            cmd (int): Command number (6-bit)
            arg (int): 32-bit arguments for the command
            crc (int): 7-bit check sum + LSB=1
            buffer (bytes): data buffer

        Returns:
            (int): the R1 response value
            buffer will contain the data
        """
        if self.debug_level >= 2:
            print(f'[SDCard] CMD_buf={cmd} ARG={arg} CRC={crc}')
        self.cs(0)
        # create and send the command
        cbuf = self.cmdbuf
        cbuf[0] = 0x40 | cmd
        cbuf[1] = arg >> 24
        cbuf[2] = arg >> 16
        cbuf[3] = arg >> 8
        cbuf[4] = arg
        cbuf[5] = crc
        self.spi.write(cbuf)

        # wait for the response (response[7] == 0)
        # try at maximum 10 times
        for i in range(10):
            self.spi.readinto(self.tokenbuf, 0xFF)
            response = self.tokenbuf[0]
            if not (response & 0x80):
                # got valid response
                if self.debug_level >= 2:
                    print(f'[SDCard] CMD_buf({cmd}) response {response}')
                # read the data
                self.spi.readinto(buffer, 0xFF)
                if self.debug_level >= 2:
                    print(' '.join(f'{byte:02x}' for byte in buffer))
                # release bus
                self.cs(1)
                self.spi.write(b"\xff")
                return response
        # timeout
        if self.debug_level >= 1:
            print(f'[SDCard] CMD_buf({cmd}) timeout!')
        self.cs(1)
        self.spi.write(b"\xff")
        return -1

    def init_card(self):
        """
        intialization sequence for SD cards (presently only V2.x type)

        Raises:
            OSError: on initalization failure
        """
        if self.debug_level >= 1:
            print(f'[SDCard] power up sequence')
        self.power_up_sequence()
        # CMD0: GO_IDLE_STATE; should return _R1_IDLE_STATE (allow 5 attempts)
        for _ in range(5):
            if self.cmd(0, 0, 0x95) == _R1_IDLE_STATE:
                break
        else:
            raise OSError("no SD card (no R1_IDLE_STAT)")
        # CMD58: READ_OCR -> Response R3
        # The first byte sent is R1. The following four bytes are the contents of the OCR register.
        # TODO: check voltage range
        response = self.cmd_buf(58, 0, 0, self.ocr)
        # MSB first
        if not self.ocr[1] & 0x7c:
            raise OSError("no voltage between 3.0V and 3.5V supported")
        if not self.ocr[0] & 0x80:
            if self.debug_level >= 1:
                print(f'[SDCard] card does not show power-up status bit - ignored')
        for _ in range(10):
            # CMD55 defines that the next command is an application specific command
            self.cmd(55, 0, 0)
            # ACMD41 activates the card intialization process
            response = self.cmd(41, 0x40000000, 0)
            if response == _R1_IDLE_STATE:
                break
            time.sleep_ms(50)
        if response != _R1_IDLE_STATE:
            raise OSError(f"timeout waiting for ACMD41 initialization (response={response})")
        # get the number of sectors
        # CMD9: read card-specific data
        # CMD9: response R2 (R1 byte + 16-byte block read)
        if self.cmd_buf(9, 0, 0, self.csd) != _R1_IDLE_STATE:
            raise OSError("no response from SD card")       
        if self.csd[0] & 0xC0 == 0x40:  # CSD version 2.0
            self.sectors = ((self.csd[8] << 8 | self.csd[9]) + 1) * 1024
            print(f'V2 : {self.sectors} sectors')
        elif self.csd[0] & 0xC0 == 0x00:  # CSD version 1.0 (old, <=2GB)
            c_size = (self.csd[6] & 0b11) << 10 | self.csd[7] << 2 | self.csd[8] >> 6
            c_size_mult = (self.csd[9] & 0b11) << 1 | self.csd[10] >> 7
            read_bl_len = self.csd[5] & 0b1111
            capacity = (c_size + 1) * (2 ** (c_size_mult + 2)) * (2**read_bl_len)
            self.sectors = capacity // 512
            print(f'V1 : {self.sectors} sectors')
        else:
            raise OSError("SD card CSD format not supported")
        if self.debug_level >= 1:
            print('[SDCard] init_card done.')

    def init_card_original(self):
        """
        # init CS pin
        self.cs.init(self.cs.OUT, value=1)

        # init SPI bus; use low data rate for initialisation
        self.init_spi(100000)

        # clock card at least 100 cycles with cs high
        for i in range(16):
            self.spi.write(b"\xff")

        # CMD0: GO_IDLE_STATE; reset - should return _R1_IDLE_STATE (allow 5 attempts)
        for _ in range(5):
            if self.cmd(0, 0, 0x95) == _R1_IDLE_STATE:
                break
        else:
            raise OSError("no SD card (no R1_IDLE_STAT)")

        # CMD8: SEND_IF_COND - determine card version
        r = self.cmd(8, 0x01AA, 0x87, 4)
        if r == _R1_IDLE_STATE:
            print("try initializing V2 card")
            self.init_card_v2()
        elif r == (_R1_IDLE_STATE | _R1_ILLEGAL_COMMAND):
            print("try initializing V1 card")
            self.init_card_v1()
        else:
            raise OSError("couldn't determine SD card version")

        # get the number of sectors
        # CMD9: read card-specific data
        # CMD9: response R2 (R1 byte + 16-byte block read)
        if self.cmd(9, 0, 0, 0, False) != 0:
            raise OSError("no response from SD card")
        self.readinto(self.csd)
        if self.csd[0] & 0xC0 == 0x40:  # CSD version 2.0
            self.sectors = ((self.csd[8] << 8 | self.csd[9]) + 1) * 1024
            print(f'V2 : {self.sectors} sectors')
        elif self.csd[0] & 0xC0 == 0x00:  # CSD version 1.0 (old, <=2GB)
            c_size = (self.csd[6] & 0b11) << 10 | self.csd[7] << 2 | self.csd[8] >> 6
            c_size_mult = (self.csd[9] & 0b11) << 1 | self.csd[10] >> 7
            read_bl_len = self.csd[5] & 0b1111
            capacity = (c_size + 1) * (2 ** (c_size_mult + 2)) * (2**read_bl_len)
            self.sectors = capacity // 512
            print(f'V1 : {self.sectors} sectors')
        else:
            raise OSError("SD card CSD format not supported")
        # print('sectors', self.sectors)

        # CMD16: set block length to 512 bytes
        if self.cmd(16, 512, 0) != 0:
            raise OSError("can't set 512 block size")

        # set to high data rate now that it's initialised
        self.init_spi(self.baudrate)
        time.sleep_ms(10)
        print(f'[SDCard] SPI frequency {self.baudrate} Hz')

        # CMD9: read card-specific data
        # this read is not necessary, thedata is already stored correctly
        # but removing this block of code breaks the subsequent card access
        if self.cmd(9, 0, 0, 0, False) != 0:
            raise OSError("no response from SD card")
        self.csd = bytearray(16)
        self.readinto(self.csd)

        # CMD10: read card identification
        if self.cmd(10, 0, 0, 0, False) != 0:
            raise OSError("no response from SD card")
        self.cid = bytearray(16)
        self.readinto(self.cid)

        # the first read fails (timeout) on a Raspberry Pico
        # we perform one dummy read
        try:
            self.readblocks(0, self.block)
        except:
            pass

        print('[SDCard] init_card done.')
        e"""

    def readblocks(self, block_num, buf, off=None):
        pass

    def writeblocks(self, block_num, buf, off=False):
        pass

    def ioctl(self, op, arg):
        if self.debug_level >= 1:
            print(f'[SDCard] ioctl(op={op},arg={arg})')
        if op == 1:  # ???
            return 0
        if op == 4:  # get number of blocks
            return self.sectors
        if op == 5:  # get block size in bytes
            return 512
        if op == 6:  # erase block
            return 0
        return 0     # default
        
    def get_CSD(self):
        """
        get the card-specific data from CMD9
        128-bit register, MSB first

        content by byte (Version 2.0):
             0: always 0x40
             1: data read access time 1
             2: data read access time 2
             3: max data transfer rate (0x32:25MHz, 0x5a:50MHz, 0x0b:100MHz, 0x2b:200MHz)
             4: card command class (12-bit)
             5: max read block length (4-bit)
             6: alignment and DSR
             7-9: device size; capacity = (C_SIZE+1)*512kByte
             ...
             15: 7-bit CRC, LSB=1
        """
        return self.csd

    def get_CID(self):
        """
        get the card ID from CMD10
        128-bit register, MSB first

        content by byte (Version 2.0):
             0: manufacturer ID
             1-2: OEM/Application ID
             3-7: product name
             8: product revision
             9-12: serial number
             13: reserved (4-bit)
             14: manufacturing date (12-bit)
             15: 7-bit CRC, LSB=1
        """
        return self.cid
