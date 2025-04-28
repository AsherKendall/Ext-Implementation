from hashlib import sha256

ENTRY_SIZE = 64
BLOCK_SIZE	= 512

def get_Inode(d, loc):
    
    inodes_blocks = ([d.readBlock(i) for i in range(2,66)])
    # Gets the block by location
    block = inodes_blocks[loc//32]
    blockLoc = loc % 32
    return Inode(block[blockLoc*16:(blockLoc*16)+16])


def to_SHA256(data):
    """Takes string and turns into MD5 hash

    Args:
        data (string): string to be hashed

    Returns:
        Bytes: MD5 hash as bytes
    """
    return sha256(data.encode('utf-8')).digest()

def to_SHA256_String(data):
    """Takes string and turns into MD5 hash string

    Args:
        data (string): string to be hashed

    Returns:
        string: MD5 hash as strings
    """
    return sha256(data.encode('utf-8')).hexdigest()

class Entry:
    
    def __init__(self, d, entry):
        entryInodeLocation = int.from_bytes(entry[:2], byteorder='little' )
        entryInode = get_Inode(d,entryInodeLocation)
        
        #print(entry[2:32])
        self.location = entryInodeLocation
        self.name = entry[2:32].decode("utf-8").rstrip('\x00')
        self.inode = entryInode
        self.size = entryInode.size
        self.type = entryInode.type
        
        self.hash = entry[32:ENTRY_SIZE].hex()


#TODO: Add support for hashmap using MD5 entries
class Entries:
    def __init__(self, entries):
        self.entries = {}
        for entry in entries:
            self.entries[entry.hash] = entry
    
    def findEntry(self, name, fileType="both"):
        hash = to_SHA256_String(name)
        if fileType == "both":
            item = self.entries.get(hash, False)
            if item and item.name == name:
                return item
        else:
            item = self.entries.get(hash, False)
            if item and item.name == name and item.type == fileType:
                return item
        return False

class Inode:
    
    def __init__(self, inode):
        self.type = 'dir' if inode[:2] ==  b'\x11\x11' else 'file'
        
        # Amount of links to file/directory
        self.link = int.from_bytes(inode[2:4], byteorder='little' )
        self.size = int.from_bytes(inode[4:8], byteorder='little' )
        self.directs = [int.from_bytes(inode[8+(i*2):10+(i*2)] , byteorder='little' )for i in range(3) ]
        self.indirects= int.from_bytes(inode[14:16] , byteorder='little' )
    def to_bytes(self):
        byte = b''
        byte = byte + b'\x11\x11' if self.type == 'dir' else b'\x22\x22'
        byte = byte + self.link.to_bytes(2, byteorder='little') + self.size.to_bytes(4, byteorder='little') 
        byte = byte + b''.join([self.directs[i].to_bytes(2, byteorder="little") for  i in range(len(self.directs))])
        byte = byte + self.indirects.to_bytes(2, byteorder='little') 
        return byte


def write_inode(d, loc, inode, BLOCK_SIZE):
    """Writes byte data to a Inode

    Args:
        d (disk): disk object
        loc (integer): location of the inode
        inode (byte string): byte string to write to inode
        BLOCK_SIZE (integer): Size of the blocks
    """
    inodeBlockLoc = (loc // 32) + 2
    temp = d.readBlock(inodeBlockLoc)
    inodeBlocks = []
    for i in range(0, BLOCK_SIZE, 16):
        inodeBlocks.append(temp[i:i+16])
    # Set new inode data
    inodeBlocks[loc % 32] = inode
    inodeBlock = b''.join(inodeBlocks)
    
    # Write modified inode block to disk
    d.writeBlock(inodeBlockLoc, inodeBlock)



def splitToList(data, size):
    return [data[i:i+size] for i in range(0, len(data), size)]

def entry_list(d, block):
    inodes = []
    for item in [block[i:i+ENTRY_SIZE] for i in range(0, len(block), ENTRY_SIZE)]:
        if item[:2] != b'\xFF\xFF':
            inodes.append(Entry(d, item))
    return Entries(inodes)

def entry_array(d, block):
    inodes = []
    for item in [block[i:i+ENTRY_SIZE] for i in range(0, len(block), ENTRY_SIZE)]:
        if item[:2] != b'\xFF\xFF':
            inodes.append(Entry(d, item))
    return inodes

def directory_bytes(block):
    entries = []
    for item in [block[i:i+ENTRY_SIZE] for i in range(0, len(block), ENTRY_SIZE)]:
        entries.append(item)
    return entries

def zero_entry(d, blockLoc, name):
    data = read_data_block(d, blockLoc)
    dirBytes = directory_bytes(data)
    for i in range(len(dirBytes)):
        iName = dirBytes[i][2:32].decode("utf-8").rstrip('\x00')
        if iName == name:
            dirBytes[i] = b'\xFF\xFF' + b'\x00' * (ENTRY_SIZE-2)
            write_data_block(d, blockLoc, b''.join(dirBytes))
            #print(f"Found entry by {name}")
            return
    #print(f"Couldn't Find entry by {name}")

def write_data_block(d, loc, data):
    d.writeBlock(loc + 66, data)

def read_data_block(d, loc):
    return d.readBlock(loc + 66)

def read_extent(d, start, length):
    return d.readBlocks(start + 66, length)

def get_first_inode(disk):
    return int(disk.inode_bitmap.index('0'))

def get_first_block(disk):
    return int(disk.block_bitmap.index('0'))




def block_list(d, inode):
    blocks = []
    for item in inode.directs:
        if item != 0:
            blocks.append(item)
    if inode.indirects != 0:
        indirectBlock = read_data_block(d, inode.indirects)
        for i in range(0,BLOCK_SIZE,4):
            start = int.from_bytes(indirectBlock[i*2:(i*2)+2], byteorder='little' )
            length = int.from_bytes(indirectBlock[i*2+2:(i*2)+4], byteorder='little' )
            if start == 0:
                break
            else:
                blocks.append((start, length))
            
    return blocks


def read_blocks(d, inode):
    blockLocs = block_list(d, inode)
    blocks = []
    print(blockLocs)
    for i in range(len(blockLocs)):
        if isinstance(blockLocs[i], tuple):
            blocks.append(read_extent(d, blockLocs[i][0], blockLocs[i][1]))
        else:
            blocks.append(read_data_block(d, blockLocs[i]))

    return blocks

