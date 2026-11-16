CPSC 471 - Programming Assignment 1: Simplified FTP
====================================================

Partners:
  1. Jesse Dawson, jesse.dawson@csu.fullerton.edu
  2. Anthony Acevedo, aracevedo@csu.fullerton.edu

Programming language: Python 3

How to run:
  1. Start the server
         python3 serv.py <PORT NUMBER> (Ex: python3 serv.py 1234)
  2. Start the client (In another terminal/directory):
        python3 cli.py <server machine> <server port>
        Ex:  python3 cli.py ecs.fullerton.edu 1234
             python3 cli.py localhost 1234 (if you are running a server locally)
  3. At the "ftp>" prompt:
         ls              list files on the server
         get <file>      download <file> from the server
         put <file>      upload <file> to the server
         quit            disconnect and exit

====================================================

PROTOCOL DESIGN
----------------

Control Connection

The client establishes a TCP connection to the server using the server's IP address and port number. This connection remains open throughout the FTP session and is used to send commands and receive status messages.

The client sends commands such as ls, get, put, and quit through the control connection. The server processes each command and sends a response indicating whether the operation can proceed or if an error occurred.

Data Connection

The program uses a separate TCP connection for transferring files and directory listings.

For each ls, get, or put command, the client creates a new TCP listening socket and binds it to port 0, allowing the operating system to assign an available ephemeral port.

The client sends this port number to the server through the control connection. The server then establishes a TCP data connection to the client's IP address and specified port.

After the data transfer finishes, the data connection is closed. A new data connection is created for the next transfer.

Message Format

Control messages are encoded using UTF-8 and preceded by a fixed 10-byte header containing the length of the message.

The length is represented as an ASCII number padded with leading zeros.

The client sends the following command formats:

ls <port>
get <port> <filename>
put <port> <filename>
quit

The server responds with:

OK          The requested operation can proceed.
DONE <n>    The operation completed successfully,
transferring n bytes.
ERR <msg>   The operation failed, with an error message.

Data transfers also begin with a 10-byte ASCII header specifying the number of bytes being transferred, followed by the actual data.

GET Operation

When the user enters get <filename>, the client creates a temporary listening socket and sends the get command, port number, and filename to the server.

The server checks whether the requested file exists. If it does not exist, the server sends an error message.

If the file exists, the server sends OK and connects to the client's data port.

The server sends the file size using the 10-byte header, followed by the file contents in chunks.

The client receives the data and writes it to a temporary file with the .part extension. Once all expected bytes have been received, the temporary file is renamed to the requested filename.

The server sends a final DONE message through the control connection after a successful transfer.

PUT Operation

When the user enters put <filename>, the client first checks whether the file exists locally.

If the file exists, the client creates a listening socket and sends the put command, port number, and filename to the server.

The server responds with OK and connects to the client's data port.

The client sends a 10-byte header containing the file size, followed by the file contents in chunks.

The server receives the data and writes it to a temporary .part file. After receiving the expected number of bytes, the server renames the temporary file to the requested filename.

The server sends DONE through the control connection when the upload completes successfully.

LS Operation

When the user enters ls, the client creates a temporary listening socket and sends the ls command with its data port number.

The server retrieves the files and directories in its current working directory using os.listdir() and sorts the results.

The server responds with OK and establishes the data connection.

The directory listing is encoded using UTF-8 and sent with a 10-byte length header.

The client receives the listing and displays it in the terminal. The server sends DONE after the operation completes.

Connection Termination

When the user enters quit, the client sends the quit command through the control connection.

The server responds with OK and closes the client's control connection.

The client then closes its control socket and exits the program.

Reliable Data Transfer

TCP does not guarantee that a single send() or recv() call will transfer all requested bytes.

To handle this, the program uses send_all() and recv_all() functions.

The send_all() function repeatedly calls send() until the specified data has been sent.

The recv_all() function repeatedly calls recv() until the requested number of bytes has been received or the connection closes.

For file transfers, the sender first transmits a 10-byte header specifying the file size. The receiver uses this size to determine how many bytes to read.

File contents are transferred in chunks of up to 65,536 bytes to avoid loading an entire file into memory.

This approach allows the client and server to transfer files larger than a single TCP buffer.

Error Handling

The server checks for invalid filenames and missing files when processing requests.

If an operation cannot proceed, the server sends an ERR message through the control connection.

During file transfers, the program checks whether the expected number of bytes was received.

If a file transfer fails, temporary .part files are removed to avoid leaving incomplete files.

The client also uses a 15-second timeout while waiting for the server to establish the data connection.

The server uses a 15-second timeout when connecting to the client's data port.

The control connection remains open between successful operations, allowing the user to execute additional FTP commands without reconnecting.
