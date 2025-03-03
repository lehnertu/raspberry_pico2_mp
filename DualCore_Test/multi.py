import time, _thread, machine

print('CPU0 starting')

running = True
delay = 0.25

# the task blinking the LED runs until the flag is cleared from CPU0
def task():
    global running, delay
    print(f'CPU1 starting')
    led = machine.Pin("LED", machine.Pin.OUT)
    while running:
        led.high()
        time.sleep(delay)
        led.low()
        time.sleep(delay)
    print('CPU1 done.')

# start the blinking task in the background
_thread.start_new_thread(task, [])

# after a while, change the frequency
time.sleep(5)
delay = 0.1
time.sleep(5)

# stop the background task
running = False
time.sleep(1)

# the execution ends with the CPU0 exiting
print('CPU0 done.')
