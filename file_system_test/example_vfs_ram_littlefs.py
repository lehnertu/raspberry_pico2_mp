# Test for VfsLittle using a RAM device

# OSError: 28 - out of memory

try:
    import vfs
    vfs.VfsLfs2
except (ImportError, AttributeError):
    print("module import error")
    raise SystemExit

class RAMBlockDevice:
    ERASE_BLOCK_SIZE = 512

    def __init__(self, blocks):
        self.data = bytearray(blocks * self.ERASE_BLOCK_SIZE)

    def readblocks(self, block, buf, off):
        print(f'[RAM-BD] readblocks(block={block},size={len(buf)},off={off})')
        addr = block * self.ERASE_BLOCK_SIZE + off
        for i in range(len(buf)):
            buf[i] = self.data[addr + i]

    def writeblocks(self, block, buf, off):
        print(f'[RAM-BD] writeblocks(block={block},size={len(buf)},off={off})')
        addr = block * self.ERASE_BLOCK_SIZE + off
        for i in range(len(buf)):
            self.data[addr + i] = buf[i]

    def ioctl(self, op, arg):
        print(f'[RAM-BD] ioctl(op={op},arg={arg})')
        if op == 1:  # ???
            return 0
        if op == 4:  # block count
            return len(self.data) // self.ERASE_BLOCK_SIZE
        if op == 5:  # block size
            return self.ERASE_BLOCK_SIZE
        if op == 6:  # erase block
            return 0
        return 0     # default

# create the RAM disk drive
bdev = RAMBlockDevice(60)

print()
print()
print('testing LittleFS2 on Ram disk')
print('=============================')
print()

print('formatting...')
vfs.VfsLfs2.mkfs(bdev, readsize=512, progsize=512, lookahead=512)

print('initialization...')
fs = vfs.VfsLfs2(bdev, readsize=512, progsize=512, lookahead=512)

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
print(list(fs.ilistdir(b"/")))

print('stat /test')
print(fs.stat("test"))

print('reading file /test')
with fs.open("test", "r") as f:
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
