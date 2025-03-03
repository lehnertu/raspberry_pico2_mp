import utime
from machine import I2C, Pin, SPI
from icm20948 import ICM20948, AccelConfig, GyroConfig
import sdcard
import vfs
import struct

print('logging ICM-20948 data')
print('----------------------')
print()

# initialize the sensor
i2c = I2C(0, freq=400_000)
imu = ICM20948(i2c, debug=False)
config = AccelConfig({'SampleRateDiv':2, 'FullScale':'4g', 'LowPass':'111.4Hz'})
imu.configureAccel(config)
config = GyroConfig({'SampleRateDiv':2, 'FullScale':'500dps', 'LowPass':'119.5Hz'})
imu.configureGyro(config)
print('ICM-20948 initialization done.')
print()

# initialize the SD card
# Assign chip select (CS) pin (and start it high)
cs = Pin(17, Pin.OUT)  # GPIO 17
cs.high()
# Initialize SPI0 peripheral
# TODO: remove defaults
spi = SPI(0,
          baudrate=25_000_000,    # 25 MHz
          polarity=0,
          phase=0,
          bits=8,
          firstbit=SPI.MSB,
          sck=Pin(18),   # GPIO 18
          mosi=Pin(19),  # GPIO 19
          miso=Pin(16))  # GPIO 16
sd = sdcard.SDCard(spi, cs)
# initialize and mount the card
card_try_counter = 0
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
print('LittleFS filesystem on SD card mounted.')
print(fs)
print()

start = utime.ticks_us()
imu._bank=0
stop = utime.ticks_us()
print(f'bank switch done in {stop-start} us')

# acquire raw data
start = utime.ticks_us()
imu.read_AccelGyro()
stop = utime.ticks_us()
print(f'read_AccelGyro takes {stop-start} us')
# print raw buffer
print(f'raw data block: {imu.acc_gyro_buf.hex()}')
print(f'scaled gyro values [dps]: ', imu.get_gyro())
print(f'scaled accel values [g]: ', imu.get_accel())

# open lig file for writing
print('opening file imu_log.dat')
f = fs.open("imu_log.dat", "wb")

start = utime.ticks_ms()
deadline = utime.ticks_add(start,10000)
# loop as fast as we can
while utime.ticks_ms() < deadline:
    # time stamp as 32-bit integer
    # it seems to reset to 0 when reaching 1e9
    timestamp = utime.ticks_us()
    imu.read_AccelGyro()
    acc = imu.get_accel()
    gyro = imu.get_gyro()
    block = struct.pack('iffffff', timestamp, acc[0], acc[1], acc[2], gyro[0], gyro[1], gyro[2])
    f.write(block)

print('closing file imu_log.dat')
f.close()
print()

print('listdir')
print(list(fs.ilistdir()))
print()

print('done.')