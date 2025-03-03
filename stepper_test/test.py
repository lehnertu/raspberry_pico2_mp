#
# Test running a stepper motor
# 
# Hardware : Polilu module with direction and step pins
#   step : GPIO16 active high
#   dir :  GPIO17
# 
# Driver : 
#   https://github.com/redoxcode/micropython-stepper
#

from machine import Pin
import time
from stepper import Stepper

print("motor start")

s1 = Stepper(16,17,steps_per_rev=2000,speed_sps=4000)

print('target position')
s1.target_deg(90)
time.sleep(2.0)
s1.target_deg(0)
time.sleep(2.0)
s1.free_run(1)

print('free running.')
time.sleep(5.0)

print("Finished.")
