#!/usr/bin/python3

import sys
import socket
import os
from datetime import datetime

MIN_PORT = 1024
MAX_PORT = 64000
MAGICNO = 0x497E
REQUEST_TYPE = 1
RESPONSE_TYPE = 2
MIN_FILENAME_LEN = 1
MAX_FILENAME_LEN = 1024
REQUEST_HEADER_LEN = 5
RESPONSE_HEADER_LEN = 8
TIMEOUT = 1

def arguemnt_check():
    """Checks that the application was run with one valid port argument and
       returns it.
       Prints an error message and exits upon failure.
    """
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0].split('/')[-1]} <port>")
        exit(1)
    port = sys.argv[1]
    if not port.isdigit() or int(port) < MIN_PORT or int(port) > MAX_PORT:
        print(f"Port must be between {MIN_PORT} and {MAX_PORT} (inclusive).")
        exit(1)
    return int(port)

def create_socket():
    """Returns a stream socket. 
       Prints an error message and exits upon failure.
    """
    try:
        soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except:
        print("Failed to create socket.")
        exit(1)
    return soc

def bind_socket(soc, port):
    """Binds socket to port. 
       Prints error message and exits upon failure.
    """
    server_ip = socket.gethostbyname(socket.gethostname())
    try:
        soc.bind((server_ip, port))
    except:
        print(f"Failed binding socket to port {port}.")
        exit(1)
        
def listen_on_socket(soc):
    """Sets the socket to listen for connections.
       Prints error message and exits upon failure.
    """
    try:
        soc.listen()
    except:
        print(f"Failed to set socket to listen for connections.")
        exit(1)
        
def accept_connection(soc):
    """Waits for an incoming connection and when one is received, prints the
       time of connection, client ip, and client port. A new socket 
       representing the connection is then returned.
    """
    try:
        conn, client_info = soc.accept()
    except:
        print("Failed to establish connection.")
        return None
    time_str = datetime.now().strftime("%H:%M:%S")
    client_ip, client_port = client_info
    print(f"Time: {time_str} IP: {client_ip} Port: {client_port}")
    sys.stdout.flush() # Prints connection information immediately
    conn.settimeout(TIMEOUT)
    return conn

def get_header(soc):
    """Receives a header over the socket and returns it.
       Prints an error message and exits if this fails.
    """
    try:
        header = bytearray(soc.recv(REQUEST_HEADER_LEN))
    except socket.timeout:
        print("Socket timed out.")
        exit(1)
    except BaseException as err:
        print(f"Failed to read data from the socket.\nError: {err}")
        exit(1)        
    return header

def is_valid_header(header):
    """Checks the validity of a FileRequest header and returns True if it's
       valid, otherwise False and prints an error message.
    """
    if len(header) == 0:
        print("Did not receive request header.")
        return False  
    magic_no = int.from_bytes(header[0:2], byteorder='big')
    if magic_no != MAGICNO:
        print(f"Received MagicNo was {magic_no}. Must be {MAGICNO}.")
        return False
    if header[2] != REQUEST_TYPE:
        print(f"Received {header[2]} in type field. Must be {REQUEST_TYPE}.")
        return False
    filename_len = int.from_bytes(header[3:5], byteorder='big')
    if filename_len < MIN_FILENAME_LEN or filename_len > MAX_FILENAME_LEN:
        print(f"Received filename length was {filename_len} bytes long." +
              f"Must be between {MIN_FILENAME_LEN} and {MAX_FILENAME_LEN} " +
              "bytes long (inclusive).")
        return False
    return True

def get_filename(header, conn):
    """Extracts the byte length of the filename from the FileRequest header, 
       then receives filename bytes and returns the filename. Prints an error
       message and returns None if the number of bytes received is not equal
       to the filename byte length.
    """
    filename_len = int.from_bytes(header[3:], byteorder='big')
    
    try:
        # Made possible to receive an extra byte to check if the client has
        # sent extra data
        filename_bytes = bytearray(conn.recv(filename_len+1))
    except socket.timeout:
        print("Socket timed out.")
        exit(1)
    except BaseException as err:
        print(f"Failed to read data from the socket.\nError: {err}")
        exit(1)     
    
    if len(filename_bytes) != filename_len:
        if len(filename_bytes) > filename_len:
            print(f"Received {len(filename_bytes)} or more filename bytes.")
        else:
            print(f"Received {len(filename_bytes)} filename bytes.")
        print(f"Expected {filename_len} bytes.")
        return None
    
    return ''.join(map(chr, filename_bytes))

def get_file_data(filename):
    """Opens the file and returns its data in a byte array.
       If it doesn't exist, and empty bytearray is returned.
    """
    try:
        file = open(filename, "rb")
    except:
        file_data = bytearray()
        if os.path.isfile(filename):
            print("Requested file couldn't be opened.")
        else:
            print("Requested file does not exist.")
    else:
        file_data = file.read()
        file.close()
    return file_data

def construct_response(file_data):
    """Constructs a FileResponse record to send back to the client and returns 
       it.
    """
    response = bytearray()
    response += MAGICNO.to_bytes(2, byteorder='big')
    response.append(RESPONSE_TYPE)
    if len(file_data) == 0:
        status_code = 0
    else:
        status_code = 1
    response.append(status_code)
    response += len(file_data).to_bytes(4, byteorder='big')
    response += file_data
    return response

def send_response(conn, response):
    """Sends response over conn socket and returns the number of bytes sent.
       Prints an error message and returns None if upon failure.
    """
    try:
        conn.sendall(response)
    except:
        print("Failed to send file.")
        return None
    return len(response)

def print_info(filename, bytes_sent):
    """Prints an informational message about the file transfer."""
    print(f"{filename} sent to client.")
    print(f"Transferred {bytes_sent} bytes.")    

def main():
    """Creates a socket that accepts connections then enters an infinite loop
       that listens for file requests and sends requested files back.
    """
    port = arguemnt_check()
    soc = create_socket()
    with soc: # Closes soc upon exiting with statement
        bind_socket(soc, port)
        listen_on_socket(soc)
        while True:
            print() # Line break to improve output readability
            sys.stdout.flush() # Prints any information from previous loop
            conn = accept_connection(soc)
            if conn is None:
                continue
            with conn: # Closes conn upon exiting with statement
                header = get_header(conn)
                if not is_valid_header(header):
                    continue
                filename = get_filename(header, conn)
                if filename is None:
                    continue
                file_data = get_file_data(filename)
                response = construct_response(file_data)
                bytes_sent = send_response(conn, response)
                if bytes_sent is not None:
                    print_info(filename, bytes_sent - RESPONSE_HEADER_LEN)
    
if __name__ == '__main__':
    main()