import machine
import sdcard

print("===============================")
print("Test of block access to SD card")
print("===============================")
print()

# Assign chip select (CS) pin (and start it high)
cs = machine.Pin(17, machine.Pin.OUT)  # GPIO 17
cs.high()

# Initialize SPI0 peripheral (start with 1 MHz)
spi = machine.SPI(0,
                  baudrate=1000000,  # 1 MHz
                  polarity=0,
                  phase=0,
                  bits=8,
                  firstbit=machine.SPI.MSB,
                  sck=machine.Pin(18),   # GPIO 18
                  mosi=machine.Pin(19),  # GPIO 19
                  miso=machine.Pin(16, machine.Pin.PULL_UP))  # GPIO 16

# Initialize SD card
# This is done with low baud rate - 100 kHz
# sd = sdcard.SDCard(spi, cs, baudrate=25_000_000, debug_level=2)
sd = sdcard.SDCard(spi, cs, baudrate=25_000_000, debug=True)
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

# get the card-specific data descriptor
csd = sd.get_CSD()
print('SD card-specific data')
print(' '.join(f'{byte:02x}' for byte in csd['raw_data']))
print(csd)
print()

# get the card ID
# cid = sd.get_CID()
# print('SD card identification')
# print(' '.join(f'{byte:02x}' for byte in cid))
# print()

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

print('reading another block')
buf = bytearray(512)
try:
    sd.readblocks(16384, buf)
    for ln in range(16):
        line = buf[ln*32:(ln+1)*32]
        print(' '.join(f'{byte:02x}' for byte in line))
except Exception as e:
    print(e)
    print('READ ERROR')
print()

print('reading block 0 again')
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
