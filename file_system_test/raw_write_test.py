import machine
import utime
import sdcard
import struct

print("===============================")
print("Test of block access to SD card")
print("===============================")
print()

# Assign chip select (CS) pin (and start it high)
cs = machine.Pin(17, machine.Pin.OUT)  # GPIO 17
cs.high()

# Initialize SPI0 peripheral
spi = machine.SPI(0,
                  baudrate=8_000_000,
                  polarity=0,
                  phase=0,
                  bits=8,
                  firstbit=machine.SPI.MSB,
                  sck=machine.Pin(18),   # GPIO 18
                  mosi=machine.Pin(19),  # GPIO 19
                  miso=machine.Pin(16, machine.Pin.PULL_UP))  # GPIO 16

# Initialize SD card
# This is done with low baud rate - 100 kHz
# The card will switch to high baudrate after initialization

sd = sdcard.SDCard(spi, cs, baudrate=8_000_000, debug=False)
print('SDCard created.')
try:
    sd.init_card()
except Exception as e:
    print('SD card initialization failed.')
    print(e)
    raise SystemExit
print('card initialization done.')
print(sd)
print()

print(f'number of blocks : {sd.ioctl(4,None)}')
print(f'blocksize : {sd.ioctl(5,None)}')
print()

# read the first block
print('reading first block')
buf = bytearray(512)
try:
    sd.readblocks(0, buf)
    for ln in range(16):
        line = buf[ln*32:(ln+1)*32]
        print(' '.join(f'{byte:02x}' for byte in line))
except Exception as e:
    print(e)
    print('READ ERROR')
print()

# read the second block
print('reading second block (that one is overwritten)')
buf = bytearray(512)
try:
    sd.readblocks(1, buf)
    for ln in range(16):
        line = buf[ln*32:(ln+1)*32]
        print(' '.join(f'{byte:02x}' for byte in line))
except Exception as e:
    print(e)
    print('READ ERROR')
print()

# read another block
print('reading 100th block (that one is overwritten)')
buf = bytearray(512)
try:
    sd.readblocks(100, buf)
    for ln in range(16):
        line = buf[ln*32:(ln+1)*32]
        print(' '.join(f'{byte:02x}' for byte in line))
except Exception as e:
    print(e)
    print('READ ERROR')
print()

# write raw 512-bit blocks as fast as possible
block = bytearray(512)
struct.pack_into('L',block,16,0x12345678)
struct.pack_into('H',block,510,0xcccc)
block_index = 0

start = utime.ticks_ms()
deadline = utime.ticks_add(start,10000)
# loop as fast as we can
while utime.ticks_ms() < deadline:
    # time stamp as 32-bit integer
    # it seems to reset to 0 when reaching 1e9
    timestamp = utime.ticks_us()
    block_index += 1
    struct.pack_into('l',block,0,timestamp)
    struct.pack_into('l',block,8,block_index)
    sd.writeblocks(block_index,block)

print(f'{block_index} blocks written.')