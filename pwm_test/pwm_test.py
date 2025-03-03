from machine import Pin, PWM
from time import sleep

led = Pin(16, Pin.OUT)
pwm = PWM(led, freq=20, duty_u16=65535)
print('full')
sleep(2.0)
print('half')
pwm.duty_u16(20000)
sleep(2.0)
print('low')
pwm.duty_u16(2000)
sleep(2.0)
print('off')
pwm.duty_u16(0)
sleep(2.0)
print('done.')
pwm.init