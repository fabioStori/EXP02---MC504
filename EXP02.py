import os
import sys
import struct
import subprocess
import argparse

out, err = subprocess.Popen("getconf PAGE_SIZE", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
VIRTUAL_PAGE_SIZE = int(out.strip())

# simple function using shifts to get the n bit from the x uint
get_bit = lambda x,n: (x & (1<<n)) >> n

# the same as * 8, as each page map entry uses 64 bits (8 bytes) shifting a page map index by 3 bits
# returns the offset in /proc/{pid}/pagemap
PAGE_MAP_ENTRY = lambda x: x << 3

# for a 4k page (the usual) that`s the same as shifting 12 bits to get the page map table index
PAGE_MAP_TABLE_INDEX = lambda x: int(x/VIRTUAL_PAGE_SIZE)


def pages_memory(pid):
    process_maps = open("/proc/%d/maps" % pid).read()
    for mapping in process_maps.split("\n")[:-1]:
        args = mapping.split(" ")
        address, perms, file_offset, dev, inode, pathname = args[0:5]+[args[-1]]
        address_start, address_end = (int(x, base=16) for x in address.split("-"))

        with open("/proc/%d/pagemap" % pid, "rb") as p:
            for page_start_address in range(address_start, address_end, 4096):
                pagemap_table_index = PAGE_MAP_TABLE_INDEX(page_start_address)
                pagemap_table_offset = PAGE_MAP_ENTRY(
                    pagemap_table_index)  # that's the byte address inside the pagemap table

                p.seek(pagemap_table_offset)
                entry = p.read(8)  # read 8 bytes (64 bits)
                entry_uint = int.from_bytes(entry, 'little')
                if get_bit(entry_uint, 63):  # page is present in ram
                    page_frame_number = entry_uint & 0x7FFFFFFFFFFFFF
                    yield page_start_address, page_frame_number


def pages_swap(pid):
    process_maps = open("/proc/%d/maps" % pid).read()
    for mapping in process_maps.split("\n")[:-1]:
        args = mapping.split(" ")
        address, perms, file_offset, dev, inode, pathname = args[0:5] + [args[-1]]
        address_start, address_end = (int(x, base=16) for x in address.split("-"))

        with open("/proc/%d/pagemap" % pid, "rb") as p:
            for page_start_address in range(address_start, address_end, 4096):
                pagemap_table_index = PAGE_MAP_TABLE_INDEX(page_start_address)
                pagemap_table_offset = PAGE_MAP_ENTRY(
                    pagemap_table_index)  # that's the byte address inside the pagemap table

                p.seek(pagemap_table_offset)
                entry = p.read(8)  # read 8 bytes (64 bits)
                entry_uint = int.from_bytes(entry, 'little')
                if get_bit(entry_uint, 62):  # swapped
                    yield page_start_address


if len(sys.argv) == 1:
    print("Usage example: python Exp2.py <PID>")
    exit(0)

pid = int(sys.argv[1])

print("Pages at swap")
for virt_addr in pages_swap(pid):
    print(hex(virt_addr >> 12))
print()
print("Pages at RAM")
print("Virtual Page Start Address - Page Frame Number")
for virt_addr, page_frame_number in pages_memory(pid):
    print("%s - %s" % (hex(virt_addr >> 12), hex(page_frame_number)))
