CPSC 471 - Programming Assignment 1: Simplified FTP
====================================================

Partners:
  1. Jesse Dawson, jesse.dawson@csu.fullerton.edu
  2. <NAME>, <EMAIL>

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
