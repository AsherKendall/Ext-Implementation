from extPack.dfuns  import splitToList, entry_list, Inode, Entry, read_data_block, write_data_block, get_first_inode, get_first_block, Entries, read_blocks, get_Inode, write_inode, block_list, zero_entry, ENTRY_SIZE, BLOCK_SIZE, to_SHA256, entry_array
import Disk

class Disk_Obj:
    
    def __init__(self, d):
        self.superBlock = d.readBlock(0)
        self.diskName = self.superBlock.rstrip(b'\x00').decode('utf-8')
        
        self.disk = d

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
        self.uDirNum = 0
        self.uDir = []
        self.cNum = 0
        self.cInode = 0
        self.cBlock = read_data_block(d, self.cDirNum)
        self.uBlock = read_data_block(d, self.cDirNum)

    def update_uDirBlock(self):
        self.uBlock = read_data_block(self.disk, self.uDirNum)
        self.cDirNum = self.uDirNum
        self.cBlock = self.uBlock
        
        
    # Dark Magic Function
    def get_path(self, path):
        splitPath = path.split('/')
        lenUDir = len(self.uDir)
        
        
        
        # Check if starting from root
        if splitPath[0] == '':
            
            # Check if just root
            if len(splitPath) > 1 and splitPath[1] == '':
                return []
            #print(splitPath)
            splitPath.pop(0)
            items = splitPath
            self.cDirNum = 0
            self.cBlock = read_data_block(self.disk, self.cDirNum)
            lenUDir = 0
        else:
            items = splitPath
            items = self.uDir + items
        # Remove '' from / at end of argument
        if items[-1] == '':
            items.pop()
        final = items.pop()
        itemLen = len(items)
        i = lenUDir
        #print(lenUDir)
        #print(items)
        while i < itemLen and len(items) > 0:
            #print(self.cDirNum)
            entries = entry_list(self.disk, self.cBlock)
            item = entries.findEntry(items[i])
            #print(items)
            if item and item.type == 'dir':
                if item.name == '.':
                    items.pop(i)
                    itemLen -= 1
                    continue
                elif item.name == '..':
                    
                    items.pop(i)
                    if len(items) > 2:
                        items.pop(i-1)
                        i -= 1
                        itemLen -= 1
                    i -= 1
                    itemLen -= 1
                    if i < 1:
                        i = 0
                        self.cDirNum = 0
                        self.cBlock = read_data_block(self.disk, self.cDirNum)
                        continue
                    item = entries.findEntry(items[i])
                
                self.cDirNum = item.inode.directs[0]
                self.cBlock = read_data_block(self.disk, self.cDirNum)
            else:
                print(f'Path not valid: {'/'.join(items)}')
                return False
            i += 1
        #print(items + [final])
        return items + [final]
        
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
        self.disk.writeBlock(1, newBitmap)
        
        # Refresh Bitmap
        bitmap_block = self.disk.readBlock(1)
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
        
        self.disk.writeBlock(1, newBitmap)
        
        
        # Refresh Bitmap
        bitmap_block = self.disk.readBlock(1)
        bitmaps = ''.join(format(byte, '08b') for byte in bitmap_block) # Turns into binary
        self.block_bitmap = bitmaps[len(bitmaps) // 2:]
        
    def write_data_bitmap_list(self, loc, length):
        for i in range (loc, loc + length+1):
            self.write_data_bitmap(i)
        
    def add_inode(self, inodeLoc, newInode):
        write_inode(self.disk, inodeLoc, newInode, BLOCK_SIZE)
        # Write modified inode
        self.write_inode_bitmap(inodeLoc)
    
    
    def remove_inode(self, inodeLoc):
        
        # Check if has more than 1 link and minus count if true
        inode = get_Inode(self.disk, inodeLoc)
        if inode.link > 1:
            inode.link = inode.link - 1
            write_inode(self.disk, inodeLoc, inode.to_bytes(), BLOCK_SIZE)
            return
        
        # Get all data blocks and remove them from data bitmap
        if inode.type == 'file':
            blocks = block_list(self.disk, inode)
            #print(blocks)
            for i in range(len(blocks)):
                if isinstance(blocks[i], tuple):
                    write_data_block(self.disk,blocks[i][0],b'\x00'* BLOCK_SIZE * (blocks[i][1] + 1))
                    self.write_data_bitmap_list(blocks[i][0],blocks[i][1])
                else:
                    write_data_block(self.disk,blocks[i],b'\x00'* BLOCK_SIZE)
                    self.write_data_bitmap(blocks[i])
        
        
        # Zero out inode
        write_inode(self.disk, inodeLoc, b'\x00' * 16, BLOCK_SIZE)
        
        # Write modified inode
        self.write_inode_bitmap(inodeLoc)
        
    def write_file_data_block(self, inodeLoc, data):
        
        dataBlocks = splitToList(data.encode('utf-8'),BLOCK_SIZE)
        # Make sure last data block is 512 bytes
        dataBlocks[-1] = dataBlocks[-1].ljust(BLOCK_SIZE, b'\x00')
        
        dataSize = len(data)
        
        
        availableBlocks = [i for i, letter in enumerate(self.block_bitmap) if letter == '0']
        # List of data block locations to be used
        usedDataBlock = []
        for i in range(len(dataBlocks)):
            newBlock = availableBlocks[i]
            usedDataBlock.append(newBlock)
            # Write to data block
            write_data_block(self.disk, newBlock, dataBlocks[i])
            self.write_data_bitmap(newBlock)
        
        inodeBytes = b'\x22\x22' + b'\x01\x00' + dataSize.to_bytes(4, byteorder="little")
        madeIndirect = False
        indirBlock = b''
        
        start = 0
        inExtent = False
        writtenBlocks = 0
        for i in range(len(usedDataBlock)):
            if i < 3:
                # Add to direct block in inode
                inodeBytes = inodeBytes + usedDataBlock[i].to_bytes(2, byteorder='little')
            else:
                # Add to indirect data block file.
                madeIndirect = True
                if usedDataBlock[i-1] + 1 == usedDataBlock[i]:
                    if not inExtent:
                        inExtent = True
                        start = usedDataBlock[i]
                        writtenBlocks = 0
                    
                    writtenBlocks += 1
                else:
                    inExtent = False
                    #print(f"start:{start} length:{writtenBlocks}")
                    indirBlock = indirBlock + start.to_bytes(2, byteorder='little') + writtenBlocks.to_bytes(2, byteorder='little')
                    start = 0
        if inExtent:
            #print(f"start:{start} length:{writtenBlocks}")
            indirBlock = indirBlock + start.to_bytes(2, byteorder='little') + writtenBlocks.to_bytes(2, byteorder='little')
        
        
        indirBlock = indirBlock.ljust(BLOCK_SIZE, b'\x00')
        
        # Get inode 
        idataLoc = get_first_block(self)
        
        if madeIndirect:
            # Write indirect dataBlock
            write_data_block(self.disk, idataLoc, indirBlock)
            inodeBytes = inodeBytes + idataLoc.to_bytes(2, byteorder='little')
            # Change block bitmap
            self.write_data_bitmap(idataLoc)
        
        
        inodeBytes.ljust(16, b'\x00')
        # Write newInode to block
        self.add_inode(inodeLoc, inodeBytes)

    #TODO: Add support multi block directories
    def add_entry(self, inodeLoc, blockLoc, name):
        dirBlock = read_data_block(self.disk, blockLoc)
        
        entries = entry_list(self.disk, dirBlock)
        item = entries.findEntry(name)
        if item:
            print("File by that name already exists")
            return True
        
        
        dBlock = [dirBlock[i:i+ENTRY_SIZE] for i in range(0, len(dirBlock), ENTRY_SIZE)]
        
        changed = False
        for i in range(len(dBlock)):
            if dBlock[i][:2] == b'\xFF\xFF':
                # Change entry
                changed = True
                dBlock[i] = (inodeLoc.to_bytes(2, byteorder='little')+ name.encode("utf-8")).ljust(32, b'\x00') + to_SHA256(name)
                break
        # Write modified directory to disk
        if changed:
            write_data_block(self.disk, blockLoc, b''.join(dBlock))
            self.cBlock = read_data_block(self.disk, self.cDirNum)
            if self.cDirNum == self.uDirNum:
                self.uBlock = read_data_block(self.disk, self.uDirNum)
            return False
        else:
            print("No space in dir for new entries")
            return True
    
    def remove_entry(self, name):
        entries = entry_list(self.disk, self.uBlock)
        item = entries.findEntry(name)
        if item:
            if item.type == 'file':
                # Remove entry
                self.remove_inode(item.location)
                zero_entry(self.disk, self.cDirNum, item.name)
                self.cBlock = read_data_block(self.disk, self.cDirNum)
            else:
                if item.inode.link > 1:
                    zero_entry(self.disk, self.cDirNum, item.name)
                    self.remove_inode(item.location)
                else:
                    subItems = []
                    zero_entry(self.disk, self.cDirNum, item.name)
                    if item.inode.link < 2:
                        subItems = subItems + ([item for item in entry_array(self.disk,read_data_block(self.disk, item.inode.directs[0]))])
                    currentDirBlock = item.inode.directs[0]
                    self.remove_inode(item.location)
                    
                    
                    while len(subItems) >= 1:
                        # Remove all files, "..", and "." from sublist
                        newList = []
                        for i in range(len(subItems)):
                            if subItems[i].name != '.' and subItems[i].name != '..':
                                if subItems[i].inode.type == 'file':
                                    self.remove_inode(subItems[i].location)
                                    zero_entry(self.disk, currentDirBlock, subItems[i].name)
                                else:
                                    newList.append(subItems[i])
                            else:
                                zero_entry(self.disk, currentDirBlock, subItems[i].name)
                        subItems = newList
                        
                        if len(subItems) > 0:
                            item = subItems.pop()
                            #print(f"Current item name : {item.name}")
                            # Add subDirectories to subitems
                            if item.name != ".." and item.name != ".":
                                #print(f"Zeroing item : {item.name}, dirBlock: {currentDirBlock}")
                                zero_entry(self.disk, currentDirBlock, item.name)
                                # Add sub items from directory if being deleted aka no links
                                if item.inode.link < 2:
                                    #print(f"This file has no links {item.name}")
                                    subItems = subItems + ([item for item in entry_array(self.disk,read_data_block(self.disk, item.inode.directs[0]))])
                                    currentDirBlock = item.inode.directs[0]
                                self.remove_inode(item.location)
    # dir Command
    # TODO: Add argument support
    def cmd_dir(self):
        entries = entry_list(self.disk, self.uBlock)
        for item in entries.entries.values():
            # Directory
            if item.type == 'dir':
                print(f' Directory  Size:{item.size:<5}  {item.name}')
            # File
            elif item.type == 'file':
                print(f' File       Size:{item.size:<5}  {item.name}')
        print()

    # cd Command
    def cmd_cd(self, name):
        path = self.get_path(name)
        if len(path) < 1:
            self.uDir = path
            self.cDirNum = 0
            self.cBlock = read_data_block(self.disk, 0)
            self.cInode = 0
            self.uDirNum = 0
            self.uBlock = read_data_block(self.disk, 0)
            return
        name = path[-1]
        entries = entry_list(self.disk, self.cBlock)
        item = entries.findEntry(name,'dir')
        if item:
            self.uDir = path
            if name == '..' or name == '.':
                self.uDir.pop()
            if name == '..' and len(self.uDir) > 0:
                self.uDir.pop()
            self.cDirNum = item.inode.directs[0]
            self.cBlock = read_data_block(self.disk, self.cDirNum)
            self.cInode = item.location
            self.uDirNum = item.inode.directs[0]
            self.uBlock = read_data_block(self.disk, self.uDirNum)
            return
        print("Directory not found!")
        print()

    # read Command
    def cmd_read(self, name):
        path = self.get_path(name)
        name = path[-1]
        entries = entry_list(self.disk, self.cBlock)
        item = entries.findEntry(name, 'file')
        if item:
            if not self.inode_bitmap[item.location]:
                return "Inode was not in bitmap"
            blocks = read_blocks(self.disk, item.inode)
            output = [i.decode("utf-8").rstrip('\x00') for i in blocks]
            print(''.join(output) )
            return

        #print(name)
        print("Sorry file by that name could not be found")

    # pwd Command
    def cmd_pwd(self):
        print(f"/{'/'.join(self.uDir)}")

    # stat Command
    def cmd_stat(self, name):
        path = self.get_path(name)
        name = path[-1]
        entries = entry_list(self.disk, self.cBlock)
        item = entries.findEntry(name)
        if item:
            print("{:<12}".format(f"Name: "), item.name)
            print("{:<12}".format(f"Inode: "), item.location)
            print("{:<12}".format(f"Type: "), item.inode.type)
            print("{:<12}".format(f"Links: "), item.inode.link)
            print("{:<12}".format(f"Size: "), item.size)
            print("{:<12}".format(f"Directs: "), item.inode.directs)
            print("{:<12}".format(f"Indirects: "), item.inode.indirects)
            return
        print("File not found")
        
    # help Command
    def cmd_help(self):
        print("dir/ls                |  List contents of current directory. Print type, size (for files), and name.")
        print("cd <dir>              |  Change directory (“cd ..” should go to the parent directory).")
        print("read <file>           |  Read and print the contents of a file.")
        print("pwd                   |  Print the current working directory.")
        print("help                  |  Lists the commands available, how to use them and what they do.") 
        print("stat                  |  Print the inode information for this file.") 
        print("write <file> <text>   |  Create a file with given name and data.") 
        print("touch <file>          |  Create a file with given name.")
        print("mkdir <dir>           |  Removes a directory and all of its subfiles.")
        print("rmdir <dir>           |  Removes a directory and all of its subfiles.")
        print("copy <file> <newFile> |  Removes a directory and all of its subfiles.")
        print("delete <file>         |  Deletes a file.")
        print("link <item> <newItem> |  Creates a hard link to a file or directory.")
        
    # write Command
    # TODO: Add write if file already exists % check if file
    def cmd_write(self, name, data):
        path = self.get_path(name)
        name = path[-1]
        # Find first unused inode
        inodeLoc = get_first_inode(self)
        
        # If entry don't already exist write the data
        entries = entry_list(self.disk, self.cBlock)
        item = entries.findEntry(name, 'file')
        if not item:
            exist = self.add_entry(inodeLoc, self.cDirNum, name)
            self.write_file_data_block(inodeLoc, data)
        else:
            print("file already exists")

    # touch Command
    # TODO: Add support for multi-block directories
    def cmd_touch(self, name):
        path = self.get_path(name)
        name = path[-1]
        # Find first unused block
        blockLoc = get_first_block(self)
        # Find first unused inode
        inodeLoc = get_first_inode(self)
        # New Inode Bytes
        newInode = b'\x22\x22' + b'\x01\x00' + (b'\00'* 4) + blockLoc.to_bytes(2, byteorder='little') + (b'\x00' * 3)
        
        # Add record to current directory
        exist = self.add_entry(inodeLoc, self.cDirNum, name)
        
        # Entry by name doesn't exist, write data, 
        if not exist:
            # Zero out block
            write_data_block(self.disk, blockLoc, (b'\x00' * BLOCK_SIZE))
            # Write newInode to block
            self.add_inode(inodeLoc, newInode)
            # Change bitmap
            self.write_data_bitmap(blockLoc)

    # mkdir Command
    def cmd_mkdir(self, name):
        path = self.get_path(name)
        name = path[-1]
        # Check if directory already exists
        entries = entry_list(self.disk, self.cBlock)
        item = entries.findEntry(name)
        if item:
            print("File or Directory already exists")
            return

        # Get new BLock
        idataLoc = get_first_block(self)
        write_data_block(self.disk, idataLoc, (b'\xFF\xFF' + b'\x00' * (ENTRY_SIZE-2)) * 8)
        
        # Get new inode
        inodeLoc = get_first_inode(self)
        newInode = (b'\x11\x11' + b'\x01\x00' + (b'\00'* 4) + idataLoc.to_bytes(2, byteorder='little')).ljust(16, b'\x00')
        #print(len(newInode))
        #print(newInode)
        
        # Create . dir
        self.add_entry(inodeLoc, idataLoc, '.')
        # Create .. dir
        self.add_entry(self.cInode, idataLoc, '..')
        
        self.add_inode(inodeLoc, newInode)
        self.add_entry(inodeLoc, self.cDirNum, name)
        
        self.write_data_bitmap(idataLoc)
    # rmdir Command
    # TODO: Add support for multi-block directories
    def cmd_rmdir(self, name):
        path = self.get_path(name)
        name = path[-1]
        
        if name == ".." or name == ".":
            print(f"Cannot delete directory {name}")
            return
        # Check if directory already exists
        entries = entry_list(self.disk, self.cBlock)
        item = entries.findEntry(name, 'dir')
        if item:
            # Remove from directory
            self.remove_entry(name)
        else:
            print(f"Directory {name} does not exist")
            return

    # delete Command
    def cmd_delete(self, name):
        path = self.get_path(name)
        name = path[-1]
        entries = entry_list(self.disk, self.cBlock)
        item = entries.findEntry(name, 'file')
        if item:
            self.remove_entry(name)
        else:
            print(f"File {name} does not exist")

    # link Command
    def cmd_link(self, file, link):
        path = self.get_path(file)
        file = path[-1]
        entries = entry_list(self.disk, self.cBlock)
        item = entries.findEntry(file)
        if item:
            # Set back to current directory
            self.update_uDirBlock()
            newPath = self.get_path(link)
            if len(newPath) < 1:
                print("not a valid file path/name")
                return
            newLink = newPath[-1]
            
            exist = self.add_entry(item.location, self.cDirNum, newLink)
            if exist:
                return
            
            # Add to link
            inode = item.inode
            inode.link += 1
            inodeBytes = inode.to_bytes()
            
            # Change inode
            write_inode(self.disk,item.location, inodeBytes, BLOCK_SIZE)
            
        else:
            print("Entry to be linked not found.")
    
    def cmd_copy(self, file, newFile):
        path = self.get_path(file)
        file = path[-1]
        entries = entry_list(self.disk, self.cBlock)
        item = entries.findEntry(file, 'file')
        if item:
            originalData = ''.join([i.decode("utf-8").rstrip('\x00') for i in read_blocks(self.disk, item.inode)])
            
            # Find first unused inode
            inodeLoc = get_first_inode(self)
            
            self.update_uDirBlock()
            # Hierarchical path for new file
            newPath = self.get_path(newFile)
            newFile = newPath[-1]
            # Add record to directory
            exist = self.add_entry(inodeLoc, self.cDirNum, newFile)
            if not exist:
                self.write_file_data_block(inodeLoc, originalData)
        else:
            print("File not found./")