
class Inode:
    
    def __init__(self, inode):
        self.type = 'dir' if inode[:2] ==  b'\x11\x11' else 'file'
        
        # Amount of links to file/directory
        self.link = int.from_bytes(inode[2:4], byteorder='little' )
        self.size = int.from_bytes(inode[4:8], byteorder='little' )
        self.directs = [int.from_bytes(inode[8+(i*2):10+(i*2)] , byteorder='little' )for i in range(3) ]
        self.indirects= int.from_bytes(inode[14:16] , byteorder='little' )



class Entry:
    
    def __init__(self, d, entry):
        entryInodeLocation = int.from_bytes(entry[:2], byteorder='little' )
        entryInode = get_Inode(d,entryInodeLocation)
        
        self.location = entryInodeLocation
        self.name = entry[2:32].decode("utf-8").rstrip('\x00')
        self.inode = entryInode
        self.size = entryInode.size
        self.type = entryInode.type




def splitToList(data, size):
    return [data[i:i+size] for i in range(0, len(data), size)]

def entry_list(d, block):
    inodes = []
    for item in [block[i:i+32] for i in range(0, len(block), 32)]:
        if item[:2] != b'\xFF\xFF':
            inodes.append(Entry(d, item))
    return inodes


