import utime
from machine import I2C, Pin
from icm20948 import ICM20948
# using ak8963.py mpu6500.py and mpu9250.py
# from mircropython-mpu9250
# from mpu9250 import MPU9250

print('ICM-20948 test')
print('--------------')
print()

i2c = I2C(0, freq=400_000)

imu = ICM20948(i2c, debug=True)
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

print()
utime.sleep_ms(100)

# read gyro only
start = utime.ticks_us()
imu.read_Gyro()
stop = utime.ticks_us()
print(f'read_Gyro takes {stop-start} us')
print(f'raw data block: {imu.gyro_buf.hex()}')
print(f'scaled values [dps]: ', imu.get_gyro())

print()
utime.sleep_ms(100)

# read gyro only
start = utime.ticks_us()
imu.read_Accel()
stop = utime.ticks_us()
print(f'read_Accel takes {stop-start} us')
print(f'raw data block: {imu.acc_buf.hex()}')
print(f'scaled values [g]: ', imu.get_accel())

print()

# read temperature
start = utime.ticks_us()
imu.read_Temp()
stop = utime.ticks_us()
print(f'read_Temp takes {stop-start} us')
print(f'raw data block: {imu.temp_buf.hex()}')
