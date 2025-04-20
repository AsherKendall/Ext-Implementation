import Disk
from mypackage.dfuns  import write_data_block

DISK_FILE	= "disk.img"
BLOCK_SIZE	= 512



size_bytes = (1 + 1 + 64 + 2048) * BLOCK_SIZE
with open('./disk.img', 'wb') as f:
    f.seek(size_bytes - 1)
    f.write(b'\x00')
print(f"Created disk image")

#Create basic file structure
d = Disk.Disk(DISK_FILE, BLOCK_SIZE)
diskName = 'Example_Disk_Image'
# Set super block
d.writeBlock(0, diskName.encode("utf-8").ljust(BLOCK_SIZE, b'\x00'))
# Set bitmap
bitmap = '1' + '0' * 2047 + '1' + '0' * 2047
bitmapBytes = bytes.fromhex(format(int(bitmap, 2), '02x'))

d.writeBlock(1, bitmapBytes)


# Set inode

inodeBlock = b'\x11\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'.ljust(BLOCK_SIZE,b'\x00')
d.writeBlock(2, bitmapBytes)

# Create root folder

data = (b'\x00\x00' + b'\x2E' + b'\x00'* 29 + b'\x00\x00' + b'\x2E\x2E' + b'\x00'* 28) + (b'\xFF\xFF' + b'\x00' * 30) * 14
d.writeBlock(66, data)