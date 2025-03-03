import machine
import sdcard
import vfs

# Assign chip select (CS) pin (and start it high)
cs = machine.Pin(17, machine.Pin.OUT)  # GPIO 17
cs.high()

# Initialize SPI0 peripheral
spi = machine.SPI(0,
                  baudrate=1_000_000,    # 1 MHz
                  polarity=0,
                  phase=0,
                  bits=8,
                  firstbit=machine.SPI.MSB,
                  sck=machine.Pin(18),   # GPIO 18
                  mosi=machine.Pin(19),  # GPIO 19
                  miso=machine.Pin(16))  # GPIO 16

# Initialize SD card
# This is done with low baud rate - 100 kHz
sd = sdcard.SDCard(spi, cs)
try:
    sd.init_card()
except Exception as e:
    print('SD card initialization failed.')
    print(e)
    raise SystemExit
print('card initialization done.')

# Mount filesystem
fs = vfs.VfsFat(sd)
print('filesystem constructor done')
vfs.mount(fs, "/sd")
print('filesystem mounted')

print('dir /')
print(list(fs.ilistdir("/")))
print()

# Create a file and write something to it
print('writing: test01.txt')
with open("/sd/test01.txt", "w") as file:
    file.write("Hello, SD World!\r\n")
    file.write("This is a test.\r\n")

print('dir /')
print(list(fs.ilistdir("/")))
print()

# Open the file we just created and read from it
print('reading: test01.txt')
with open("/sd/test01.txt", "r") as file:
    data = file.read()
    print(data)

print('reading: README')
with open("/sd/README", "r") as file:
    data = file.read()
    print(data)
