import utime
from machine import Pin, SPI
import sdcard
import vfs
import struct

print('LittleFS on SD card speed test')
print('------------------------------')
print()

# initialize the SD card
# Assign chip select (CS) pin (and start it high)
cs = Pin(17, Pin.OUT)  # GPIO 17
cs.high()
# Initialize SPI0 peripheral
# TODO: remove defaults
# SPI1 default pins 10, 11, 8
spi = SPI(0,
          baudrate=8_000_000,    # 25 MHz
          polarity=0,
          phase=0,
          bits=8,
          firstbit=SPI.MSB,
          sck=Pin(18),   # GPIO 18
          mosi=Pin(19),  # GPIO 19
          miso=Pin(16))  # GPIO 16
sd = sdcard.SDCard(spi, cs, baudrate=8_000_000, debug=True)
# initialize and mount the card
card_try_counter = 0
good = False
while not good:
    try:
        sd.init_card()
        fs = vfs.VfsLfs2(sd, readsize=512, progsize=512, lookahead=512)
        vfs.mount(fs, "/sd")
    except Exception as e:
        card_try_counter += 1
        print(e)
        print(f'SD card mounting failed on {card_try_counter} try.')
        if card_try_counter >= 3:
            print('SD card mounting failed on 3 times - aborting.')
            raise SystemExit
        utime.sleep_ms(500)
    else:
        good=True
print('LittleFS filesystem on SD card mounted.')
print(fs)
print()

# open lig file for writing
print('opening file speed_test.dat')
f = fs.open("speed_test.dat", "wb")

block = bytearray(16)
start = utime.ticks_ms()
deadline = utime.ticks_add(start,10000)
# loop as fast as we can
while utime.ticks_ms() < deadline:
    # time stamp as 32-bit integer
    # it seems to reset to 0 when reaching 1e9
    timestamp = utime.ticks_us()
    struct.pack_into('l',block,0,timestamp)
    f.write(block)

print('closing file speed_test.dat')
f.close()
print()

print('listdir')
print(list(fs.ilistdir()))
print()

print('done.')