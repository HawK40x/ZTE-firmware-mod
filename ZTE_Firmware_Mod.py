#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

import lzma
import os
import sys
import binascii
import struct
import mmap
import time
import argparse
import io

# Check arguments
parser = argparse.ArgumentParser(description='ZTE Firmware Mod Tool - ONLY for F601v6')

parser.add_argument('memory_dump', help='path to the Memory dump file')
parser.add_argument('firmware_version', help='patch firmware version')
parser.add_argument('output_file', help='path to the output file')
args = parser.parse_args()

if not all([args.memory_dump, args.firmware_version, args.output_file]):
    parser.print_help()
    sys.exit(1)

file_name = args.memory_dump
fw_version = args.firmware_version
output_file = args.output_file

def accept_warning():
    print("---------------------------------------")
    print(
        f"This script is currently working only for ZTE F601v6 shipped with TIM (V6.0.10N40) or OpenFiber (V6.0.10P6N7) firmware\r\n"
        f"All other versions were not tested, USE IT AT YOUR OWN RISK!\r\n"
        f"Before proceed make sure to have a GOOD BACKUP of all your ONT partitions.\r\n"
        f"Please refer to Hack-GPON Wiki for how-to: https://hack-gpon.github.io/ont-zte-f601/\r")
    print("---------------------------------------")
    count = 0
    while True:
        user_input = input("To proceed please enter 'y', otherwise 'n' to exit: ")
        if user_input.lower() in ['y', 'yes']:
            print("\r\n")
            check_file_exists(file_name)
            
            with open(file_name, 'r+b') as f:
                with mmap.mmap(f.fileno(), 0) as mm:
                    check_file(mm)
                    patch_zImage(mm, fw_version, output_file)
                    print_install()
            break
        elif user_input.lower() in ['n', 'no']:
            print("Ok, bye! :)")
            sys.exit(1)
        else:
            count = count + 1
            print("Invalid input, pls try again..")
            if count > 3:
                print("Too many attempts, bye! :)")
                sys.exit(1)

def print_install():
    print("\r\n")
    print("---------------------------------------")
    print("How to flash: \r\n")
    print(f"Copy firmware file {output_file} into your TFTP server and flash is using this procedure on the ONT over telnet:\r\n"
          f"\r\n"
          f"cd /var/tmp\r\n"
          f"tftp -l fw.bin -r {output_file} 192.168.1.100 -g\r\n"
          f"fw_flashing -d 0 -r 0 -c 1 -f fw.bin\r\n"
          f"\r\n"
          f"After you get prompt back, erase old configurations:\r\n"
          f"\r\n"
          f"rm /userconfig/cfg/*.xml\r\n"
          f"\r\n"
          f"Create dummy files for HW\SWVer spoofing:\r\n"
          f"!!! CHANGE IT BASED ON YOUR ORIGINAL ONT !!!\r\n"
          f"echo V6.0 > /userconfig/cfg/hwver\r\n"
          f"echo {fw_version} > /userconfig/cfg/swver\r\n"
          f"\r\n"
          f"Then run these commands to switch software bank and reboot the ONT:\r\n"
          f"\r\n"
          f"upgradetest switchver\r\n"
          f"reboot")
    print("---------------------------------------")
    print("Good luck!")

def check_file_exists(file_name):
    if not os.path.isfile(file_name):
        print(f"ERROR: Memory Dump {file_name} does not exist!")
        sys.exit(1)
    if os.path.isfile(output_file):
        print(f"WARNING: {output_file} already exist, it will be deleted!")
        os.remove(output_file)

# Check if the dump is a correct ZTE file and match HWVer
def check_file(mm):
    # Check ZTE Magic Header
    if mm[4:12] != b"DDDDUUUU":
        print(f"ERROR: {file_name} doesn't seem a valid F601v6 dump")
        sys.exit(1)
        return False

    # Check HW Version
    hwver = mm[144:145].decode("utf-8").strip('\x00')
    if hwver != '6':
        print("Wrong HW version, only V6 is supported!")
        sys.exit(1)
        return False

    # Proceed with other steps
    return True

def patch_zImage(mm, fw_version, output_file):
    last_time = time.time()
    print("---------------------------------------")
    print("Step 1: Patching zImage and fix uImage Header..")
    # Open zImage and strip uImage Header
    zte_header = mm[:256]
    content = mm[320:]

    # Open the mmap object as a LZMA file
    with lzma.open(io.BytesIO(content), format=lzma.FORMAT_ALONE, mode='r') as f:
        uncompressed_content = f.read()
        # Patching data
        patch_data = uncompressed_content
        patch_data = patch_data.replace(b'/proc/csp/hardVersion', b'/userconfig/cfg/hwver')
        patch_data = patch_data.replace(b'/proc/csp/softVersion', b'/userconfig/cfg/swver')
        patch_data = patch_data.replace(b'-luser', b'-ldev\x00')
        pos = patch_data.find(b'/etc/shadow\x00\x00\x00root')
        if pos != -1:
            pos += len(b'/etc/shadow\x00\x00\x00root:')
            end_pos = patch_data.find(b':', pos)
            if end_pos != -1:
                to_replace = patch_data[pos:end_pos]
                patch_data = patch_data[:pos] + patch_data[end_pos:]
                pos = patch_data.find(b'bin:!!')
                if pos != -1:
                    patch_data = patch_data[:pos+4] + to_replace + patch_data[pos+4:]

        # Needed to put it back on the LZMA header for Uboot decompression, missing on latest Python LZMA implementation
        uncompressed_size: int = len(patch_data)

        # Write the patched data to a new LZMA file in memory
        with io.BytesIO() as f:
            with lzma.open(f, format=lzma.FORMAT_ALONE, mode='w') as f2:
                f2.write(patch_data)
            data = f.getvalue()

        # Fix missing LZMA decompress size header in memory
        data = data[:5] + uncompressed_size.to_bytes(8, 'little') + data[13:]

        # Add back uImage Header
        header_data = bytearray.fromhex('27051956ceb1a22560e69d25004ea4d7' +
                                        '40008000400080000133c9ff05020203' +
                                        '4c696e7578204b65726e656c20496d61' +
                                        '67650000000000000000000000000000' )
        # Reset CRC32 of the Header
        header_data[4:8] = [0, 0, 0, 0]

        # Rewrite new file size
        file_size = len(data)
        header_data[13:16] = file_size.to_bytes(3, byteorder='big')

        # Rewrite new zImage CRC32
        crc_zImage = binascii.crc32(data)
        header_data[24:28] = crc_zImage.to_bytes(4, byteorder='big')

        # Calculate new header CRC32 with new size\zImage CRC32
        crc = binascii.crc32(header_data)
        header_data[4:8] = crc.to_bytes(4, byteorder='big')

        # Write new zImage with new header
        new_zImage = header_data + data
        elapsed_time = time.time() - last_time
        print(f"------: Done in {round(elapsed_time, 3)} secs")

    last_time = time.time()
    print("Step 2: Add back ZTE Header and Firmware Version..")

    # Check fw_version length, display warning if more than 15 characters
    fw_version_bytes = fw_version.encode('utf-8')
    if len(fw_version_bytes) > 15:
        fw_version = fw_version[:15]
        print("FW length more than 15 characters, it will be cut!")
    file_size = len(new_zImage)
    zte_header_size = len(zte_header)

    # Update firmware version, print output only if different from the one in the original header
    old_version_string = zte_header[36:52].decode("utf-8").strip('\x00')
    zte_header = zte_header[:36] + bytes(fw_version, 'utf-8').ljust(16, b'\x00') + zte_header[52:]
    new_version_string = zte_header[36:52].decode("utf-8").strip('\x00')
    if old_version_string != new_version_string:
        print(f"------: Old FW version {old_version_string}")
        print(f"------: New FW version {new_version_string}")

    # Update file size
    zte_header = zte_header[:72] + struct.pack("<I", file_size) + zte_header[76:]

    # Update total size
    total_size = zte_header_size + file_size
    zte_header = zte_header[:88] + struct.pack("<I", total_size) + zte_header[92:]

    # Update file CRC32
    crc = binascii.crc32(new_zImage, 0) & 0xffffffff
    zte_header = zte_header[:80] + struct.pack("<I", crc) + zte_header[84:]

    # Update header CRC32
    zte_header_crc = binascii.crc32(zte_header[20:184], 0) & 0xffffffff
    zte_header = zte_header[:184] + struct.pack("<I", zte_header_crc) + zte_header[188:]
    elapsed_time = time.time() - last_time
    print(f"------: Done in {round(elapsed_time, 3)} secs")
    last_time = time.time()

    print("Step 3: Write firmware file..")
    # Write new file for firmware upgrade
    with open(output_file, 'wb') as f:
        f.write(zte_header)
        f.write(new_zImage)
    elapsed_time = time.time() - last_time
    print(f"------: Done in {round(elapsed_time, 3)} secs")

accept_warning()
