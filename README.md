# COSC264-File-Server
## Introduction
This is a command-line file server that uses TCP sockets. It includes one application for the server and one for the client.

## How to Run
### Server
Navigate to the server folder with
```
cd server
```
Then run the server application with
```
python server.py <port>
```
Arguments:
- ```port``` specifies the port the server will run on. The port can be between 1,024 and 64,000 (inclusive).

After the server has been started, it will listen for any requests from the client and send back any files requested.
The server will log requests to the command line with the time, client ip address, client port, file requested, and number of bytes transferred.

### Client
Navigate to the client folder with
```
cd client
```
Then run the server application with
```
python client.py <ip_address> <port> <filename>
```
Arguments:
- ```ip_address``` ip address of the server
- ```port``` port the server is running on
- ```filename``` name of the file to retrieve

The client will download the specified file from the server if it exists and display the size, time taken, and average download speed.
