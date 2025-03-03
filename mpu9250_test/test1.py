import utime
from machine import I2C, Pin

# using ak8963.py mpu6500.py and mpu9250.py
# from mircropython-mpu9250
from mpu9250 import MPU9250

i2c = I2C(0, freq=400_000)
print(i2c.scan())

imu = MPU9250(i2c)
print(imu)
print(i2c.scan())

