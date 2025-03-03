import vfs

class RAMBlockDevice:
    ERASE_BLOCK_SIZE = 512

    def __init__(self, blocks):
        self.data = bytearray(blocks * self.ERASE_BLOCK_SIZE)

    def readblocks(self, block, buf, off=0):
        addr = block * self.ERASE_BLOCK_SIZE + off
        for i in range(len(buf)):
            buf[i] = self.data[addr + i]

    def writeblocks(self, block, buf, off=None):
        if off is None:
            # erase, then write
            off = 0
        addr = block * self.ERASE_BLOCK_SIZE + off
        for i in range(len(buf)):
            self.data[addr + i] = buf[i]

    def ioctl(self, op, arg):
        if op == 4:  # block count
            return len(self.data) // self.ERASE_BLOCK_SIZE
        if op == 5:  # block size
            return self.ERASE_BLOCK_SIZE
        if op == 6:  # erase block
            return 0

bdev = RAMBlockDevice(50)
vfs_class = vfs.VfsLfs2
print("testing ", vfs_class)
vfs_class.mkfs(bdev)
vfs = vfs_class(bdev)

# open, write close
f = vfs.open("test", "w")
for i in range(5):
    f.write(f'some data {i}\n')
f.close()

# open, write close
f = vfs.open("test2", "w")
for i in range(100):
    f.write(f'some data {i}\n')
f.close()

# read
with vfs.open("test", "r") as f:
    print(f.read())

# ilistdir
# returns an iterator yielding tuples
# the tuples have the form (name, type, inode[, size]):
print(list(vfs.ilistdir()))

# statvfs
# Returns a tuple with the filesystem information in the following order:
# f_bsize – file system block size
# f_frsize – fragment size
# f_blocks – size of fs in f_frsize units
# f_bfree – number of free blocks
# f_bavail – number of free blocks for unprivileged users
# f_files – number of inodes
# f_ffree – number of free inodes
# f_favail – number of free inodes for unprivileged users
# f_flag – mount flags
# f_namemax – maximum filename length
print(vfs.statvfs("/"))

# read the first block
buf = bytearray(bdev.ERASE_BLOCK_SIZE)
bdev.readblocks(0, buf)
for ln in range(10):
    line = buf[ln*16:(ln+1)*16]
    print(line)
