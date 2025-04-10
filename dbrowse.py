import Disk
import math


DISK_FILE	= "disk.img"
BLOCK_SIZE	= 512

# Disk FIle
d = Disk.Disk(DISK_FILE, BLOCK_SIZE)



def splitToList(data, size):
    return [data[i:i+size] for i in range(0, len(data), size)]

class Inode:
    
    def __init__(self, inode):
        self.type = 'dir' if inode[:2] ==  b'\x11\x11' else 'file'
        
        # Amount of links to file/directory
        self.link = int.from_bytes(inode[2:4], byteorder='little' )
        self.size = int.from_bytes(inode[4:8], byteorder='little' )
        self.directs = [int.from_bytes(inode[8+(i*2):10+(i*2)] , byteorder='little' )for i in range(3) ]
        self.indirects= int.from_bytes(inode[14:16] , byteorder='little' )


    
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

def entry_list(d, block):
    inodes = []
    for item in [block[i:i+32] for i in range(0, len(block), 32)]:
        if item[:2] != b'\xFF\xFF':
            inodes.append(Entry(d, item))
    return inodes

def block_list(inode):
    blocks = []
    inodes = [inode]
    # Add all directs to list
    print()
    while True:
        
        if len(inodes) <= 0:
            break
        # Takes first Inode off the list
        newNode = inodes.pop(0)
        
        for item in newNode.directs:
            if item != 0:
                blocks.append(d.readBlock(item + 66))
        if newNode.indirects != 0:
            indirectBlock = d.readBlock(newNode.indirects + 66)
            for i in range(0,512,2):
                loc = int.from_bytes(indirectBlock[i*2:(i*2)+2], byteorder='little' )
                if loc == 0:
                    break
                else:
                    blocks.append(d.readBlock(loc + 66))
            
    return blocks


class Disk:
    
    def __init__(self, d):
        self.superBlock = d.readBlock(0)

        bitmap_block = d.readBlock(1)
        bitmaps = ''.join(format(byte, '08b') for byte in bitmap_block) # Turns into binary
        self.inode_bitmap = bitmaps[:len(bitmaps) // 2]
        self.block_bitmap = bitmaps[len(bitmaps) // 2:]
        inodes_blocks = ([d.readBlock(i) for i in range(2,66)])  #2-65
        
        self.inodes = []
        # Separates INodes in to array of 16 bytes
        for i in range(len(inodes_blocks)):
            block = inodes_blocks[i]
            # Inodes per Block
            for y in range(int(len(block)/16)):
                self.inodes.append(Inode(block[y*16:(y*16)+16]))
                
                
        self.cDirNum = 0
        self.cDir = []
        self.cNum = 0
        self.cBlock = d.readBlock(self.cDirNum + 66)


    
        
    def write_inode_bitmap(self, loc):
        string_list = list(self.inode_bitmap)
        if self.inode_bitmap[loc] == '1':
            string_list[loc] = '0'
        else:
            string_list[loc] = '1'
        self.inode_bitmap = "".join(string_list)
        # Convert to Bytes
        blockBitmap = bytes.fromhex(format(int(self.block_bitmap, 2), '02x'))
        inodeBitmap = bytes.fromhex(format(int(self.inode_bitmap, 2), '02x'))
        newBitmap = inodeBitmap + blockBitmap
        d.writeBlock(1, newBitmap)
        
        # Refresh Bitmap
        bitmap_block = d.readBlock(1)
        bitmaps = ''.join(format(byte, '08b') for byte in bitmap_block) # Turns into binary
        
        self.inode_bitmap = bitmaps[:len(bitmaps) // 2]
        
    def write_data_bitmap(self, loc):
        string_list = list(self.block_bitmap)
        if self.block_bitmap[loc] == '1':
            string_list[loc] = '0'
        else:
            string_list[loc] = '1'
        self.block_bitmap = "".join(string_list)
        # Convert to Bytes
        blockBitmap = bytes.fromhex(format(int(self.block_bitmap, 2), '02x'))
        inodeBitmap = bytes.fromhex(format(int(self.inode_bitmap, 2), '02x'))
        newBitmap =  inodeBitmap + blockBitmap
        
        d.writeBlock(1, newBitmap)
        
        
        # Refresh Bitmap
        bitmap_block = d.readBlock(1)
        bitmaps = ''.join(format(byte, '08b') for byte in bitmap_block) # Turns into binary
        self.block_bitmap = bitmaps[len(bitmaps) // 2:]
        
        
    def add_inode(self, inodeLoc, newInode):
        inodeBlockLoc = (inodeLoc // 32) + 2
        temp = d.readBlock(inodeBlockLoc)
        inodeBlocks = []
        for i in range(0, BLOCK_SIZE, 16):
            inodeBlocks.append(temp[i:i+16])
        # Set new inode data
        inodeBlocks[inodeLoc % 32] = newInode
        inodeBlock = b''.join(inodeBlocks)
        
        # Write modified inode block to disk
        d.writeBlock(inodeBlockLoc, inodeBlock)
        
        # Write modified inode
        self.write_inode_bitmap(inodeLoc)
        
        
    def write_file_data_block(self, data):
        
        dataBlocks = splitToList(data.encode('utf-8'),512)
        # Make sure last data block is 512 bytes
        dataBlocks[-1].ljust(512, b'\x00')
        
        dataSize = len(data)
        
        
        availableBlocks = [i for i, letter in enumerate(self.block_bitmap) if letter == '0']
        print(availableBlocks)
        # List of data block locations to be used
        usedDataBlock = []
        for i in range(len(dataBlocks)):
            newBlock = availableBlocks[i]
            usedDataBlock.append(newBlock)
            # Write to data block
            d.writeBlock(newBlock + 66, dataBlocks[i])
            self.write_data_bitmap(newBlock)
        
        
        inodeBytes = b'\x22\x22' + b'\x01\x00' + dataSize.to_bytes(4, byteorder="little")
        madeIndirect = False
        indirBlock = b''
        for i in range(len(usedDataBlock)):
            if i < 3:
                # Add to direct block in inode
                inodeBytes = inodeBytes + usedDataBlock[i].to_bytes(2, byteorder='little')
            else:
                # Add to indirect data block file.
                madeIndirect = True
                indirBlock = indirBlock + usedDataBlock[i].to_bytes(2, byteorder='little')
                print()
        
        
        indirBlock = indirBlock.ljust(512, b'\x00')
        
        # Get inode 
        inodeLoc = int(self.inode_bitmap.index('0'))
        idataLoc = int(self.block_bitmap.index('0'))
        
        if madeIndirect:
            # Write indirect dataBlock
            d.writeBlock(idataLoc + 66, indirBlock)
            inodeBytes = inodeBytes + idataLoc.to_bytes(2, byteorder='little')
            # Change block bitmap
            self.write_data_bitmap(idataLoc)
        
        
        inodeBytes.ljust(16, b'\x00')
        # Write newInode to block
        self.add_inode(inodeLoc, inodeBytes)
        return inodeLoc

    def add_entry(self, inodeLoc, name):
        dBlock = [self.cBlock[i:i+32] for i in range(0, len(self.cBlock), 32)]
        changed = False
        for i in range(len(dBlock)):
            if dBlock[i][:2] == b'\xFF\xFF':
                # Change entry
                changed = True
                dBlock[i] = (inodeLoc.to_bytes(2, byteorder='little')+ name.encode("utf-8")).ljust(32, b'\x00')
                break
        # Write modified directory to disk
        if changed:
            d.writeBlock(self.cDirNum + 66, b''.join(dBlock))
            self.cBlock = d.readBlock(self.cDirNum + 66)
        else:
            print("No space in dir for new entries")
    
    

    # dir Command
    def cmd_dir(self):
        entries = entry_list(d, self.cBlock)
        for item in entries:
            # Directory
            if item.type == 'dir':
                print(f' Directory  Size:{item.size:<5}  {item.name}')
            # File
            elif item.type == 'file':
                print(f' File       Size:{item.size:<5}  {item.name}')
        print()

    # cd Command
    def cmd_cd(self, name):
        entries = entry_list(d, self.cBlock)
        for item in entries:
            if item.name == name and item.type == 'dir':
                if name == '..' and len(self.cDir) > 0:
                    self.cDir.pop()
                elif name != '.' and name != '..':
                    self.cDir.append(item.name)
                self.cDirNum = item.inode.directs[0]
                self.cBlock = d.readBlock(self.cDirNum + 66)
                return
        print("Directory not found!")
        print()

    # read Command
    def cmd_read(self, name):
        entries = entry_list(d, self.cBlock)
        for item in entries:
            if item.name == name and item.type == 'file':
                if not self.inode_bitmap[item.location]:
                    return "Inode was not in bitmap"
                blocks = block_list(item.inode)
                output = [i.decode("utf-8").rstrip('\x00') for i in blocks]
                print(''.join(output) )
                return
        print("Sorry file by that name could not be found")

    # pwd Command
    def cmd_pwd(self):
        print(f"\\{'\\'.join(self.cDir)}")

    # stat Command
    def cmd_stat(self, name):
        entries = entry_list(d, self.cBlock)
        for item in entries:
            if item.name == name:
                print("{:<12}".format(f"Name: "), item.name)
                print("{:<12}".format(f"Inode: "), item.location)
                print("{:<12}".format(f"Type: "), item.inode.type)
                print("{:<12}".format(f"Links: "), item.inode.link)
                print("{:<12}".format(f"Size: "), item.size)
                print("{:<12}".format(f"Directs: "), item.inode.directs)
                print("{:<12}".format(f"Indirects: "), item.inode.indirects)
                return
    # help Command
    def cmd_help(self):
        print("dir          |  List contents of current directory. Print type, size (for files), and name")
        print("cd <dir>     |  Change directory (“cd ..” should go to the parent directory)")
        print("read <file>  |  Read and print the contents of a file")
        print("pwd          |  Print the current working directory.")
        print("help         |  Lists the commands available, how to use them and what they do.") 
        print("stat         |  Print the inode information for this file.") 
        print("write        |  Create a file with given name and data.") 
        print("touch        |  Create a file with given name.") 
        
    # write Command
    # TODO: Add write if file already exists % check if file
    # TODO: Add new data structure to indirects
    def cmd_write(self, name, data):
        # Find first unused inode
        inodeLoc = self.write_file_data_block(data)
        # Add record to current directory
        self.add_entry(inodeLoc, name)

    # touch Command
    def cmd_touch(self, name):
        # Find first unused block
        blockLoc = int(self.block_bitmap.index('0'))
        # Find first unused inode
        inodeLoc = int(self.inode_bitmap.index('0'))
        # Zero out block
        d.writeBlock(blockLoc + 66, (b'\x00' * BLOCK_SIZE))
        # New Inode Bytes
        newInode = b'\x22\x22' + b'\x01\x00' + (b'\00'* 4) + blockLoc.to_bytes(2, byteorder='little') + (b'\x00' * 3)
        # Write newInode to block
        self.add_inode(inodeLoc, newInode)
        
        # Add record to current directory
        self.add_entry(inodeLoc, name)
        
        # Change bitmap
        self.write_data_bitmap(blockLoc)

    # mkdir Command
    # TODO: Add support for multi-block directories
    def cmd_mkdir(self, name):
        print("mkdir")
        
    # rmdir Command
    def cmd_rmdir(self, name):
        print("rmdir")

    # delete Command
    # TODO: Check for multiple links and remove if 0
    def cmd_delete(self):
        print("delete")

    # link Command
    def cmd_link(self):
        print("link")

disk = Disk(d)

while(True):
    print()
    inp = input(f"D:\\{'\\'.join(disk.cDir)}>")
    print()
    
    split = inp.split()
    
    #TODO: Add support for hierarchical paths
    
    if inp == "dir":
        disk.cmd_dir()
    elif inp == "pwd":
        disk.cmd_pwd()
    elif inp == "help":
        disk.cmd_help()
    if split:
        if split[0] == "cd" and len(split) == 2:
            disk.cmd_cd(split[1])
        elif split[0] == "read" and len(split) == 2:
            disk.cmd_read(split[1])
        elif split[0] == "stat" and len(split) == 2:
            disk.cmd_stat(split[1])
        elif split[0] == "touch" and len(split) == 2:
            disk.cmd_touch(split[1])
        elif split[0] == "write" and len(split) > 2:
            disk.cmd_write(split[1], ''.join(split[2:]))

