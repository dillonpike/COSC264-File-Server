#!/usr/bin/python3

import sys
import socket
import os
import time
from datetime import datetime

MIN_PORT = 1024
MAX_PORT = 64000
MAGICNO = 0x497E
REQUEST_TYPE = 1
RESPONSE_TYPE = 2
MAX_FILENAMELEN = 1024
TIMEOUT = 1
RESPONSE_HEADER_LEN = 8
DATA_BLOCK_SIZE = 4096

def arguemnt_check():
    """Checks that the application was run with three valid ip, port, and
       filename arguments and returns them.
    """
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0].split('/')[-1]} <ip> <port> <filename>")
        exit(1)

    try:
        ip = socket.getaddrinfo(sys.argv[1], None)[0][-1][0]
    except:
        print("Invalid IP address or domain name.")
        exit(1)

    port = sys.argv[2]
    if not port.isdigit() or int(port) < MIN_PORT or int(port) > MAX_PORT:
        print(f"Port must be between {MIN_PORT} and {MAX_PORT} (inclusive).")
        exit(1)
    port = int(port)
    
    filename = sys.argv[3]
    if os.path.isfile(filename):
        try:
            open(filename)
        except:
            pass
        else:
            print("File already exists and can be opened locally.")
            exit(1)
            
    return ip, port, filename

def create_socket(timeout=None):
    """Returns a stream socket with a given timeout (no timeout by default).
       Prints an error message and exits upon failure.
    """
    try:
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except:
        print("Failed to create socket.")
        exit(1)
    soc.settimeout(timeout)
    return soc

def connect_to_server(soc, ip, port):
    """Connects the socket to the ip address on the given port.
       Prints an error message and exits if this fails.
    """
    try:
        soc.connect((ip, port))
    except:
        print("Couldn't connect to the server.")
        exit(1)
        
def construct_request(filename):
    """Returns a FileRequest record to send to the server."""
    request = bytearray()
    request += MAGICNO.to_bytes(2, byteorder='big')
    request.append(REQUEST_TYPE)
    file_bytes = filename.encode()
    request += len(file_bytes).to_bytes(2, byteorder='big')
    request += file_bytes
    return request

def get_header(soc):
    """Receives a header over the socket and returns it.
       Prints an error message and exits if this fails.
    """
    try:
        header = bytearray(soc.recv(RESPONSE_HEADER_LEN))
    except socket.timeout:
        print("Socket timed out.")
        exit(1)
    except BaseException as err:
        print(f"Failed to read data from the socket.\nError: {err}")
        exit(1)
    return header

def validate_header(header):
    """Checks the validity of a FileResponse header and prints an error message
       and exits if it's not valid.
    """
    if len(header) == 0:
        print("Did not receive response header.")
        exit(1)
    magic_no = int.from_bytes(header[0:2], byteorder='big')
    if magic_no != MAGICNO:
        print(f"Received MagicNo was {magic_no}. Must be {MAGICNO}.")
        exit(1)
    if header[2] != RESPONSE_TYPE:
        print(f"Received {header[2]} in type field. Must be {RESPONSE_TYPE}.")
        exit(1)
    if header[3] not in [0, 1]:
        print(f"Received StatusCode was {header[3]} bytes long. " +
              f"Must be 0 or 1.")
        exit(1)

def check_status_code(header):
    """If the StatusCode in header is 0 then an informational message is 
       printed and the application exits.
    """
    if header[3] == 0:
        print("File couldn't be found or opened on the server.")
        exit(1)
        
def receive_data_block(soc):
    """Receives a data block over the socket and returns it. Upon failure, an
       appropriate error message is printed and returns None.
    """
    try:
        data_block = bytearray(soc.recv(DATA_BLOCK_SIZE))
    except socket.timeout:
        print("Socket timed out.")
        data_block = None
    except BaseException as err:
        print(f"Failed to read data from the socket.\nError: {err}")
        data_block = None
    return data_block
        
def write_to_file(file, data):
    """Writes data to file. Prints an error message and exits upon failure."""
    try:
        file.write(data)
    except:
        print("Failed to write data to the file.")
        remove_file(file)
        exit(1)    
        
def save_file(soc, filename, header):
    """Creates a file with the given filename. Then receives 4096 byte blocks
       of data over the socket and writes them to the file until no more data 
       is received. Upon failure, an appropriate error message is printed and 
       the application exists.
    """
    try:
        file = open(filename, "wb")
    except:
        print("Failed to create the file.")
        exit(1)
        
    data_length = int.from_bytes(header[4:8], byteorder='big')
    total_bytes = 0
    data_block = b' '
    print("Downloading...")
    sys.stdout.flush() # Prints downloading message immediately
    while len(data_block) > 0:
        data_block = receive_data_block(soc)
        if data_block is None:
            file.close()
            remove_file(file)
            exit(1)
        write_to_file(file, data_block)
        total_bytes += len(data_block)
    file.close()
        
    if data_length != total_bytes:
        print(f"Received {total_bytes} bytes.\nExpected {data_length} bytes.")
        remove_file(file)
        exit(1)
        
    return total_bytes

def remove_file(file):
    """Removes file from storage."""
    try:
        os.remove(file.name)
    except:
        print("File couldn't be removed.")
        
def print_info(filename, total_bytes, time_taken):
    """Prints an informational message about the successful file download."""
    print(f"Successfully downloaded {filename}.\nSize: {total_bytes} bytes.")
    print(f"Time Taken: {time_taken:.4f} s")
    if time_taken != 0:
        download_speed = total_bytes / (time_taken) / 10**6
        print(f"Average download speed: {download_speed:.2f} MB/s")
    else:
        print(f"Download time was too short to measure the download speed.")

def main():
    """Requests the file from the server (both given as parameters) then saves 
       it when received.
    """
    server_ip, port, filename = arguemnt_check()
    soc = create_socket(TIMEOUT)
    with soc: # Closes soc upon exiting with statement
        connect_to_server(soc, server_ip, port)
        request = construct_request(filename)
        soc.sendall(request)
        header = get_header(soc)
        validate_header(header)
        check_status_code(header)
        start_time = time.time()
        total_bytes = save_file(soc, filename, header)
        end_time = time.time()
        print_info(filename, total_bytes, end_time - start_time)

if __name__ == '__main__':
    main()