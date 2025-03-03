import time, _thread, machine

print('CPU0 starting')
delay = 0.25

def task(n):
    global delay
    print(f'CPU1 starting for {n} flashes')
    led = machine.Pin("LED", machine.Pin.OUT)
    for i in range(n):
        led.high()
        time.sleep(delay)
        led.low()
        time.sleep(delay)
    print('CPU1 done')

_thread.start_new_thread(task, (10,))

time.sleep(10)
print('CPU0 done')