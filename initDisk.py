import Disk
from mypackage.dfuns  import write_data_block, BLOCK_SIZE, ENTRY_SIZE
from hashlib import sha256
import argparse
import sys

DISK_FILE	= "disk.img"

if len(sys.argv) > 1:
    arguments = sys.argv[1:]
    print("Arguments passed:", arguments)

parser = argparse.ArgumentParser(description="Script for initializing disk image")
parser.add_argument("name", type=str, help="Your name")
args = parser.parse_args()

size_bytes = (1 + 1 + 64 + 2048) * BLOCK_SIZE
with open('./disk.img', 'wb') as f:
    f.seek(size_bytes - 1)
    f.write(b'\x00')
print(f"Created disk image")

#Create basic file structure
d = Disk.Disk(DISK_FILE, BLOCK_SIZE)
diskName = args.name
# Set super block
d.writeBlock(0, diskName.encode("utf-8").ljust(BLOCK_SIZE, b'\x00'))
# Set bitmap
bitmap = '1' + '0' * 2047 + '1' + '0' * 2047
bitmapBytes = bytes.fromhex(format(int(bitmap, 2), '02x'))

d.writeBlock(1, bitmapBytes)


# Set inode

inodeBlock = b'\x11\x11\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'.ljust(BLOCK_SIZE,b'\x00')
d.writeBlock(2, inodeBlock)

# Create root folder

sDot = b'\x00\x00' + b'\x2E' + b'\x00'* 29 + sha256('.'.encode('utf-8')).digest()
dDot = b'\x00\x00' + b'\x2E\x2E' + b'\x00'* 28 + sha256('..'.encode('utf-8')).digest()
data = sDot + dDot + (b'\xFF\xFF' + b'\x00' * (ENTRY_SIZE -2)) * 6
d.writeBlock(66, data)