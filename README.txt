CPSC 471 - Programming Assignment 1: Simplified FTP
====================================================

Partners:
  1. Jesse Dawson, jesse.dawson@csu.fullerton.edu
  2. Anthony Acevedo, aracevedo@csu.fullerton.edu
  3. Joseph Scarnecchia, josephdscarnecchia@csu.fullerton.edu

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


PROTOCOL DESIGN
---------------
The client opens one TCP control connection to the server port supplied on
the command line. It stays open until quit. Commands and status messages
use a 10-byte ASCII decimal length header followed by UTF-8 text.

For ls, get, and put, the client binds a second TCP listening socket to
port 0, receives an available port, and sends the port with its command.
The server connects back to that port for the data transfer, then closes
the data connection. The control connection remains open.

Commands: ls <port>, get <port> <filename>, put <port> <filename>, quit.
Responses: OK before transfer, DONE <bytes> after success, or ERR <message>
if an operation fails. quit receives OK.

For ls, the server sends a directory listing. For get, the server sends
the file to the client. For put, the client sends the file to the server.
Each data transfer begins with a 10-byte ASCII decimal byte count followed
by that many bytes. The receiver reads until the expected count is reached.
The client and server use repeated send() and recv() calls because one call
may transfer fewer bytes than requested. Files are read in chunks, and
received files use a temporary .part file until complete.