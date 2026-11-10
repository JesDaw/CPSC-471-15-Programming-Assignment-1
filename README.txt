CPSC 471 - Programming Assignment 1: Simplified FTP
====================================================

Partners:
  1. Jesse Dawson, jesse.dawson@csu.fullerton.edu
  2. <NAME>, <EMAIL>

Programming language: Python 3 (tested with 3.8+; standard library only)

Files:
  serv.py       FTP server
  cli.py        FTP client
  PROTOCOL.txt  Application-layer protocol design

How to run:
  1. Start the server (from the directory whose files you want to serve):
         python3 serv.py <PORT NUMBER>
     e.g.   python3 serv.py 1234

  2. In another terminal / directory, start the client:
         python3 cli.py <server machine> <server port>
     e.g.   python3 cli.py ecs.fullerton.edu 1234
            python3 cli.py localhost 1234

  3. At the "ftp>" prompt:
         ls              list files on the server
         get <file>      download <file> from the server
         put <file>      upload <file> to the server
         quit            disconnect and exit

Notes:
  * Two connections are used: a control channel for the whole session and a
    new data channel per ls/get/put (client listens on an ephemeral port,
    server connects to it). See PROTOCOL.txt.
  * Binary and large files are supported (length-prefixed, chunked transfer).
  * The server prints SUCCESS/FAILURE for each request; the client prints
    the file name and byte count after each get/put.
  * The server's file names may not contain path separators.
  * The server handles multiple clients (one thread per client).
  * The client must be reachable by the server for the data channel (works on
    localhost and the lab network; NAT/firewalls may block it).
