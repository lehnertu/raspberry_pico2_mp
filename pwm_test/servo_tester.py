from machine import Pin, PWM
import time
from servo import Servo

s1_pin = Pin(16, Pin.OUT)
servo1 = Servo(s1_pin, rate=50.0, symmetric=True)

while True:
    # run into one end position
    for int_pos in range(101):
        servo1.set_position(0.01*int_pos)
        time.sleep_ms(10)
    print('right')
    # run back to zero
    for int_pos in range(100):
        servo1.set_position(0.01*(99-int_pos))
        time.sleep_ms(10)
    print('zero')
    time.sleep_ms(1000)
    # run into other end position
    for int_pos in range(101):
        servo1.set_position(-0.01*int_pos)
        time.sleep_ms(10)
    print('left')
    # run back to zero
    for int_pos in range(100):
        servo1.set_position(-0.01*(99-int_pos))
        time.sleep_ms(10)
    print('zero')
    time.sleep_ms(1000)
