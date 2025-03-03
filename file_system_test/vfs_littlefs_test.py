import machine
import sdcard
import vfs

print('\n\n\n *** LittleFS on SD card ***\n')

# Assign chip select (CS) pin (and start it high)
cs = machine.Pin(17, machine.Pin.OUT)  # GPIO 17
cs.high()

# Initialize SPI0 peripheral
spi = machine.SPI(0,
                  baudrate=8_000_000,    # 1 MHz
                  polarity=0,
                  phase=0,
                  bits=8,
                  firstbit=machine.SPI.MSB,
                  sck=machine.Pin(18),   # GPIO 18
                  mosi=machine.Pin(19),  # GPIO 19
                  miso=machine.Pin(16))  # GPIO 16

# Initialize SD card
print('initializing SD card')
# This is done with low baud rate - 100 kHz
sd = sdcard.SDCard(spi, cs, debug=True)
try:
    sd.init_card()
except Exception as e:
    print('SD card initialization failed.')
    print(e)
    raise SystemExit
print('card initialization done.')
print()

# print('creating Lfs2 file system on SD')
# vfs.VfsLfs2.mkfs(sd, readsize=512, progsize=512, lookahead=512)
# print('done.')

# Mount filesystem
print('mounting Lfs2 file system on SD')
fs = vfs.VfsLfs2(sd, readsize=512, progsize=512, lookahead=512)
print('filesystem constructor done')
vfs.mount(fs, "/sd")
print('filesystem mounted')
print()

print('stat /')
print(fs.statvfs("/"))
print()

print('create one file')
f = fs.open("test", "w")
f.write("testing LittleFS")
f.close()

print('stat /')
print(fs.statvfs("/"))
print()

print('ilistdir')
print(list(fs.ilistdir()))
print(list(fs.ilistdir("/")))

print('stat /test')
print(fs.stat("test"))

print('reading file /test')
with fs.open("test", "r") as f:
    print(f.read())
print()

print('reading file /README.md')
with fs.open("README.md", "r") as f:
    print(f.read())
print()

print('writing large file')
with fs.open("testbig", "w") as f:
    data = "large012" * 32 * 16
    print("data length:", len(data))
    for i in range(4):
        print("write", i)
        f.write(data)

print('stat /')
print(fs.statvfs("/"))
