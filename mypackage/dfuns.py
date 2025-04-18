

def get_Inode(d, loc):
    
    inodes_blocks = ([d.readBlock(i) for i in range(2,66)])
    # Gets the block by location
    block = inodes_blocks[loc//32]
    blockLoc = loc % 32
    return Inode(block[blockLoc*16:(blockLoc*16)+16])



class Entry:
    
    def __init__(self, d, entry):
        entryInodeLocation = int.from_bytes(entry[:2], byteorder='little' )
        entryInode = get_Inode(d,entryInodeLocation)
        
        self.location = entryInodeLocation
        self.name = entry[2:32].decode("utf-8").rstrip('\x00')
        self.inode = entryInode
        self.size = entryInode.size
        self.type = entryInode.type


class Entries:
    def __init__(self, entries):
        self.entries = entries
    
    
    def findEntry(self, name, fileType="both"):
        if fileType == "both":
            for item in self.entries:
                if item.name == name:
                    return item
        else:
            for item in self.entries:
                if item.name == name and item.type == fileType:
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
    for item in [block[i:i+32] for i in range(0, len(block), 32)]:
        if item[:2] != b'\xFF\xFF':
            inodes.append(Entry(d, item))
    return Entries(inodes)


def write_data_block(d, loc, data):
    d.writeBlock(loc + 66, data)

def read_data_block(d, loc):
    return d.readBlock(loc + 66)

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
        for i in range(0,512,2):
            loc = int.from_bytes(indirectBlock[i*2:(i*2)+2], byteorder='little' )
            if loc == 0:
                break
            else:
                blocks.append(loc)
            
    return blocks


#TODO: Add support for extents
def read_blocks(d, inode):
    blockLocs = block_list(d, inode)
    blocks = []
    for i in range(len(blockLocs)):
        blocks.append(read_data_block(d, blockLocs[i]))
    return blocks

