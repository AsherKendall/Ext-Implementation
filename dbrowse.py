import Disk
import math
from extPack.dfuns  import splitToList, entry_list, Inode, Entry, read_data_block, write_data_block, get_first_inode, get_first_block, Entries, read_blocks, get_Inode, write_inode, block_list, zero_entry, ENTRY_SIZE, BLOCK_SIZE, to_SHA256, entry_array
from extPack.filesystem import Disk_Obj
DISK_FILE	= "disk.img"

# Disk FIle
d = Disk.Disk(DISK_FILE, BLOCK_SIZE)


disk = Disk_Obj(d)

print(f"Browsing Disk: {disk.diskName}")

while(True):
    try:
        print()
        inp = input(f"D:/{'/'.join(disk.uDir)}>")
        print()
        
        split = inp.split()
        lenSplit = len(split)
        # Hierarchical path code
        if lenSplit > 1:
            
            items = split[1].split('/')
            secondItem = split[1]
            
            if lenSplit > 1:
                match split[0]:
                    case "cd":
                        if lenSplit == 2:
                            disk.cmd_cd(secondItem)
                    case "read":
                        if lenSplit == 2:
                            disk.cmd_read(secondItem)
                    case "stat":
                        if lenSplit == 2:
                            disk.cmd_stat(secondItem)
                    case "touch":
                        if lenSplit == 2:
                            disk.cmd_touch(secondItem)
                    case "mkdir":
                        if lenSplit == 2:
                            disk.cmd_mkdir(secondItem)
                    case "delete":
                        if lenSplit == 2:
                            disk.cmd_delete(secondItem)
                    case "rmdir":
                        if lenSplit == 2:
                            disk.cmd_rmdir(secondItem)
                    case "write":
                        if lenSplit > 2:
                            disk.cmd_write(secondItem, ' '.join(split[2:]))
                    case "copy":
                        if lenSplit > 2:
                            disk.cmd_copy(secondItem, split[2])
                    case "link":
                        if lenSplit > 2:
                            disk.cmd_link(secondItem, split[2])
            
        else:
            match inp:
                case "dir" | "ls":
                    disk.cmd_dir()
                case"pwd":
                    disk.cmd_pwd()
                case "help":
                    disk.cmd_help()
                case _:
                    print("Command not found")
        disk.update_uDirBlock()
    except KeyboardInterrupt:
        print()
        print("Exited Program")
        exit()