"""
MicroPython driver for SD cards using SPI bus.

for further information see:
    http://elm-chan.org/docs/mmc/mmc_e.html
    https://www.it-sd.com/articles/secure-digital-card-registers/

Requires an SPI bus and a CS pin.  Provides readblocks and writeblocks
methods so the device can be mounted as a filesystem.

Example usage on pyboard:

    import pyb, sdcard, os
    sd = sdcard.SDCard(pyb.SPI(1), pyb.Pin.board.X5)
    pyb.mount(sd, '/sd2')
    os.listdir('/')

Example usage on ESP8266:

    import machine, sdcard, os
    sd = sdcard.SDCard(machine.SPI(1), machine.Pin(15))
    os.mount(sd, '/sd')
    os.listdir('/')

"""

from machine import Pin
from micropython import const
import time
from util import *

_CMD_TIMEOUT = const(100)

_R1_IDLE_STATE = const(1 << 0)
# R1_ERASE_RESET = const(1 << 1)
_R1_ILLEGAL_COMMAND = const(1 << 2)
# R1_COM_CRC_ERROR = const(1 << 3)
# R1_ERASE_SEQUENCE_ERROR = const(1 << 4)
# R1_ADDRESS_ERROR = const(1 << 5)
# R1_PARAMETER_ERROR = const(1 << 6)
_TOKEN_CMD25 = const(0xFC)
_TOKEN_STOP_TRAN = const(0xFD)
_TOKEN_DATA = const(0xFE)


class SDCard:
    def __init__(self, spi, cs, baudrate=1_000_000, debug=False):
        self.spi = spi
        self.cs = cs
        self.baudrate = baudrate
        self.debug = debug
        if self.debug:
            self.trigger = Pin(20, Pin.OUT, value=0)
        self.cmdbuf = bytearray(6)
        self.dummybuf = bytearray(512)
        self.tokenbuf = bytearray(1)
        for i in range(512):
            self.dummybuf[i] = 0xFF
        self.dummybuf_memoryview = memoryview(self.dummybuf)
        self.csd = bytearray(16)
        self.cid = bytearray(16)

    def init_spi(self, baudrate):
        try:
            master = self.spi.MASTER
        except AttributeError:
            # on ESP8266 and RPi2
            if self.debug:
                print(f'setting baud rate to {baudrate}.')
            self.spi.init(baudrate=baudrate, phase=0, polarity=0)
        else:
            # on pyboard
            self.spi.init(master, baudrate=baudrate, phase=0, polarity=0)

    def init_card(self):
        if self.debug:
            print('[SDcard] init_card()')
        # init CS pin
        self.cs.init(self.cs.OUT, value=1)

        # init SPI bus; use low data rate for initialisation
        self.init_spi(100000)
        if self.debug:
            print('init_spi done.')

        # clock card at least 100 cycles with cs high
        for i in range(16):
            self.spi.write(b"\xff")

        # CMD0: init card; should return _R1_IDLE_STATE (allow 5 attempts)
        for _ in range(5):
            response = self.cmd(0, 0, 0x95)
            if response == _R1_IDLE_STATE:
                break
            time.sleep_ms(50)
        if response != _R1_IDLE_STATE:
            raise OSError(f"no SD card - CMD(0) responds {response}")
        if self.debug:
            print(f'CMD(0) responds {_R1_IDLE_STATE}.')

        # CMD8: determine card version
        r = self.cmd(8, 0x01AA, 0x87, 4)
        if r == _R1_IDLE_STATE:
            if self.debug:
                print(f'CMD(8) responds {r} -> V2.x card.')
            self.init_card_v2()
        elif r == (_R1_IDLE_STATE | _R1_ILLEGAL_COMMAND):
            if self.debug:
                print(f'CMD(8) responds {r} -> V1.x card.')
            self.init_card_v1()
        else:
            raise OSError("couldn't determine SD card version")

        # get the number of sectors
        # CMD9: read card-specific data
        # CMD9: response R2 (R1 byte + 16-byte block read)
        response = self.cmd(9, 0, 0, 0, False)
        if self.debug:
            print(f'CMD(9) responds {response}')
        if response != 0:
            raise OSError("no response from SD card")
        self.readinto(self.csd)
        if self.debug:
            print('CSD: '+' '.join(f'{byte:02x}' for byte in self.csd))
        if self.csd[0] & 0xC0 == 0x40:  # CSD version 2.0
            self.sectors = ((self.csd[8] << 8 | self.csd[9]) + 1) * 1024
        elif self.csd[0] & 0xC0 == 0x00:  # CSD version 1.0 (old, <=2GB)
            c_size = (self.csd[6] & 0b11) << 10 | self.csd[7] << 2 | self.csd[8] >> 6
            c_size_mult = (self.csd[9] & 0b11) << 1 | self.csd[10] >> 7
            read_bl_len = self.csd[5] & 0b1111
            capacity = (c_size + 1) * (2 ** (c_size_mult + 2)) * (2**read_bl_len)
            self.sectors = capacity // 512
        else:
            raise OSError("SD card CSD format not supported")
        # print('sectors', self.sectors)

        # CMD16: set block length to 512 bytes
        if self.cmd(16, 512, 0) != 0:
            raise OSError("can't set 512 block size")

        # set to high data rate now that it's initialised
        self.init_spi(self.baudrate)

        # perform one dummy block read
        try:
            self.readblocks(0, self.dummybuf)
        except Exception as e:
            print(e)
            print('READ ERROR on first block read.')
        print()


    def init_card_v1(self):
        for i in range(_CMD_TIMEOUT):
            time.sleep_ms(50)
            self.cmd(55, 0, 0)
            if self.cmd(41, 0, 0) == 0:
                # SDSC card, uses byte addressing in read/write/erase commands
                self.cdv = 512
                # print("[SDCard] v1 card")
                return
        raise OSError("timeout waiting for v1 card")

    def init_card_v2(self):
        for i in range(_CMD_TIMEOUT):
            time.sleep_ms(50)
            self.cmd(58, 0, 0, 4)
            self.cmd(55, 0, 0)
            if self.cmd(41, 0x40000000, 0) == 0:
                self.cmd(58, 0, 0, -4)  # 4-byte response, negative means keep the first byte
                ocr = self.tokenbuf[0]  # get first byte of response, which is OCR
                if not ocr & 0x40:
                    # SDSC card, uses byte addressing in read/write/erase commands
                    self.cdv = 512
                else:
                    # SDHC/SDXC card, uses block addressing in read/write/erase commands
                    self.cdv = 1
                # print("[SDCard] v2 card")
                return
        raise OSError("timeout waiting for v2 card")

    def cmd(self, cmd, arg, crc, final=0, release=True, skip1=False):
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

        if skip1:
            self.spi.readinto(self.tokenbuf, 0xFF)

        # wait for the response (response[7] == 0)
        for i in range(_CMD_TIMEOUT):
            self.spi.readinto(self.tokenbuf, 0xFF)
            response = self.tokenbuf[0]
            if not (response & 0x80):
                # this could be a big-endian integer that we are getting here
                # if final<0 then store the first byte to tokenbuf and discard the rest
                if final < 0:
                    self.spi.readinto(self.tokenbuf, 0xFF)
                    final = -1 - final
                for j in range(final):
                    self.spi.write(b"\xff")
                if release:
                    self.cs(1)
                    self.spi.write(b"\xff")
                return response

        # timeout
        self.cs(1)
        self.spi.write(b"\xff")
        return -1

    def readinto(self, buf):
        self.cs(0)
        if self.debug:
            print(f'sdcard.readinto size {len(buf)}')
            self.trigger.high()
        # read until start byte (0xfe)
        for i in range(_CMD_TIMEOUT):
            self.spi.readinto(self.tokenbuf, 0xFF)
            if self.tokenbuf[0] == _TOKEN_DATA:
                break
            time.sleep_ms(1)
        else:
            self.cs(1)
            if self.debug:
                self.trigger.low()
            raise OSError("timeout in readinto() waiting for DATA token")

        # read data
        mv = self.dummybuf_memoryview
        if len(buf) != len(mv):
            mv = mv[: len(buf)]
        self.spi.write_readinto(mv, buf)

        # read checksum
        self.spi.write(b"\xff")
        self.spi.write(b"\xff")

        self.cs(1)
        if self.debug:
            self.trigger.low()
        self.spi.write(b"\xff")

    def write(self, token, buf):
        self.cs(0)
        if self.debug:
            self.trigger.high()

        # send: start of block, data, checksum
        self.spi.read(1, token)
        self.spi.write(buf)
        self.spi.write(b"\xff")
        self.spi.write(b"\xff")

        # check the response
        if (self.spi.read(1, 0xFF)[0] & 0x1F) != 0x05:
            if self.debug:
                self.trigger.low()
            self.cs(1)
            self.spi.write(b"\xff")
            return

        # wait for write to finish
        while self.spi.read(1, 0xFF)[0] == 0:
            pass

        self.cs(1)
        self.spi.write(b"\xff")
        if self.debug:
            self.trigger.low()

    def write_token(self, token):
        self.cs(0)
        self.spi.read(1, token)
        self.spi.write(b"\xff")
        # wait for write to finish
        while self.spi.read(1, 0xFF)[0] == 0x00:
            pass

        self.cs(1)
        self.spi.write(b"\xff")

    def readblocks(self, block_num, buf, offset=0):
        if self.debug:
            print(f'[SDCard] readblocks() : block={block_num}')
        if offset != 0:
             raise OSError(f'[SDCard] readblocks() offset={offset} not supported')
        # workaround for shared bus, required for (at least) some Kingston
        # devices, ensure MOSI is high before starting transaction
        self.spi.write(b"\xff")
        nblocks = len(buf) // 512
        assert nblocks and not len(buf) % 512, "Buffer length is invalid"
        if nblocks == 1:
            # CMD17: set read address for single block
            response = self.cmd(17, block_num * self.cdv, 0, release=False)
            if response != 0:
                # release the card
                self.cs(1)
                self.spi.write(b"\xff")
                raise OSError(f'[SDCard] readblocks() CMD(17) responds {response}')
            # receive the data
            self.readinto(buf)
        else:
            # CMD18: set read address for multiple blocks
            response = self.cmd(18, block_num * self.cdv, 0, release=False)
            if response != 0:
                # release the card
                self.cs(1)
                self.spi.write(b"\xff")
                raise OSError(f'[SDCard] readblocks() CMD(18) responds {response}')
            offset = 0
            mv = memoryview(buf)
            while nblocks:
                # receive the data and release card
                self.readinto(mv[offset : offset + 512])
                offset += 512
                nblocks -= 1
            response = self.cmd(12, 0, 0xFF, skip1=True)
            if response != 0:
                # release the card
                self.cs(1)
                self.spi.write(b"\xff")
                raise OSError(f'[SDCard] readblocks() CMD(12) responds {response}')
        # release the card
        self.cs(1)
        self.spi.write(b"\xff")

    def writeblocks(self, block_num, buf, offset=0):
        if self.debug:
            print(f'[SDCard] writeblocks() : block={block_num}')
        if offset != 0:
             raise OSError(f'[SDCard] writeblocks() offset={offset} not supported')
        # workaround for shared bus, required for (at least) some Kingston
        # devices, ensure MOSI is high before starting transaction
        self.spi.write(b"\xff")
        nblocks, err = divmod(len(buf), 512)
        assert nblocks and not err, "Buffer length is invalid"
        if nblocks == 1:
            # CMD24: set write address for single block
            response = self.cmd(24, block_num * self.cdv, 0)
            if response != 0:
                raise OSError(f'[SDCard] writeblocks() CMD(24) responds {response}')
            # send the data
            self.write(_TOKEN_DATA, buf)
        else:
            # CMD25: set write address for first block
            response = self.cmd(25, block_num * self.cdv, 0)
            if response != 0:
                raise OSError(f'[SDCard] writeblocks() CMD(25) responds {response}')
            # send the data
            offset = 0
            mv = memoryview(buf)
            while nblocks:
                self.write(_TOKEN_CMD25, mv[offset : offset + 512])
                offset += 512
                nblocks -= 1
            self.write_token(_TOKEN_STOP_TRAN)
        # release the card
        self.cs(1)
        self.spi.write(b"\xff")

    def ioctl(self, op, arg):
        if op == 4:  # get number of blocks
            return self.sectors
        if op == 5:  # get block size in bytes
            return 512
        if op == 6:  # erase block
            if self.debug:
                print(f'[SDCard] ioctl(6) explicit erase not supported')
            return 0
        return 0     # default

    def get_CSD(self):
        """
        get the card-specific data from CMD9
        128-bit register, MSB first

        content by byte (Version 2.0):
        """
        val = dict({'raw_data':self.csd})
        structure = extract_bit_field(self.csd,126,2)
        if structure == 1:
            val.update(version='2.0')
            size = extract_bit_field(self.csd,48,22)
            val.update(num_blocks=size+1)
        elif structure == 0:
            val.update({'version':'1.0'})
            c_size = extract_bit_field(self.csd,62,12)
            c_mult = extract_bit_field(self.csd,47,3)
            read_bl_len = extract_bit_field(self.csd,80,4)
            val.update({'block_size':2**read_bl_len})
            val.update({'num_blocks':(c_size + 1) * (2 ** (c_size_mult + 2))})
        else:
            val.update({'version':'unknown'})
        # both versions identical
        size = extract_bit_field(self.csd,39,7)
        val.update({'erase_size':size})
        return val
