# *****************************************************************
# cli.py - simplified FTP client (CPSC471 Programming Assignment 1)
#
# Usage: python3 cli.py <server machine> <server port>
#
# Commands:
#   ftp> get <file name>   download a file from the server
#   ftp> put <file name>   upload a file to the server
#   ftp> ls                list files on the server
#   ftp> quit              disconnect and exit
#
# The first connection (control channel) lasts the whole session.
# For every ls/get/put the client opens an ephemeral port, tells the
# server about it over the control channel, and the SERVER connects
# back to that port to form the data channel.
# *****************************************************************
import os
import socket
import sys

HEADER_LEN = 10
CHUNK = 65536
ACCEPT_TIMEOUT = 15      # seconds to wait for the server to connect back


def recv_all(sock, num_bytes):
    """Receive exactly num_bytes (fewer only if the peer closed)."""
    buf = bytearray()
    while len(buf) < num_bytes:
        tmp = sock.recv(min(CHUNK, num_bytes - len(buf)))
        if not tmp:
            break
        buf += tmp
    return bytes(buf)


def send_all(sock, data):
    sent = 0
    while sent < len(data):
        sent += sock.send(data[sent:])


def send_msg(sock, text):
    payload = text.encode("utf-8")
    send_all(sock, str(len(payload)).zfill(HEADER_LEN).encode("ascii") + payload)


def recv_msg(sock):
    header = recv_all(sock, HEADER_LEN)
    if len(header) != HEADER_LEN:
        return None
    size = int(header)
    payload = recv_all(sock, size)
    if len(payload) != size:
        return None
    return payload.decode("utf-8")


def open_listener():
    """Bind to port 0 so the OS picks a free ephemeral port."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    s.listen(1)
    s.settimeout(ACCEPT_TIMEOUT)
    return s, s.getsockname()[1]


def request(ctrl, request_fmt, filename=None):
    """
    Common start of ls/get/put. Opens the ephemeral listener, sends the
    request, and waits for the server's OK/ERR on the control channel.
    Returns (listener, error). If error is not None, listener is None.
    """
    listener, port = open_listener()
    msg = request_fmt + " " + str(port)
    if filename is not None:
        msg += " " + filename
    send_msg(ctrl, msg)

    reply = recv_msg(ctrl)
    if reply is None:
        listener.close()
        raise ConnectionError("server closed the control connection")
    if reply != "OK":
        listener.close()
        return None, reply[4:] if reply.startswith("ERR ") else reply
    return listener, None


def accept_data(listener):
    try:
        data_sock, _ = listener.accept()
    finally:
        listener.close()           # one data connection per transfer
    return data_sock


def final_status(ctrl):
    """Read the server's closing status for a transfer."""
    reply = recv_msg(ctrl)
    if reply is None:
        raise ConnectionError("server closed the control connection")
    if reply.startswith("DONE"):
        return None
    return reply[4:] if reply.startswith("ERR ") else reply


def cmd_ls(ctrl):
    listener, err = request(ctrl, "ls")
    if err:
        print("ls failed:", err)
        return
    data_sock = accept_data(listener)
    try:
        header = recv_all(data_sock, HEADER_LEN)
        size = int(header)
        listing = recv_all(data_sock, size)
    finally:
        data_sock.close()
    err = final_status(ctrl)
    if err:
        print("ls failed:", err)
        return
    sys.stdout.write(listing.decode("utf-8"))


def cmd_get(ctrl, name):
    listener, err = request(ctrl, "get", name)
    if err:
        print("get failed:", err)
        return
    data_sock = accept_data(listener)
    tmp_name = name + ".part"
    try:
        header = recv_all(data_sock, HEADER_LEN)
        if len(header) != HEADER_LEN:
            raise IOError("data connection closed early")
        size = int(header)
        received = 0
        with open(tmp_name, "wb") as f:
            while received < size:
                chunk = data_sock.recv(min(CHUNK, size - received))
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
        if received != size:
            raise IOError("incomplete transfer (%d of %d bytes)" % (received, size))
        os.replace(tmp_name, name)
    except Exception as e:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        data_sock.close()
        final_status(ctrl)
        print("get failed:", e)
        return
    data_sock.close()
    err = final_status(ctrl)
    if err:
        print("get failed:", err)
        return
    print("Downloaded %s (%d bytes)" % (name, received))


def cmd_put(ctrl, name):
    if not os.path.isfile(name):
        print("put failed: local file '%s' not found" % name)
        return
    size = os.path.getsize(name)
    listener, err = request(ctrl, "put", name)
    if err:
        print("put failed:", err)
        return
    data_sock = accept_data(listener)
    try:
        send_all(data_sock, str(size).zfill(HEADER_LEN).encode("ascii"))
        with open(name, "rb") as f:
            while True:
                chunk = f.read(CHUNK)
                if not chunk:
                    break
                send_all(data_sock, chunk)
    finally:
        data_sock.close()
    err = final_status(ctrl)
    if err:
        print("put failed:", err)
        return
    print("Uploaded %s (%d bytes)" % (name, size))


def main():
    if len(sys.argv) != 3:
        print("USAGE: python3 %s <server machine> <server port>" % sys.argv[0])
        sys.exit(1)

    server_name = sys.argv[1]
    try:
        server_port = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer")
        sys.exit(1)

    ctrl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        ctrl.connect((server_name, server_port))   # DNS lookup happens here
    except (socket.error, socket.gaierror) as e:
        print("Could not connect to %s:%d - %s" % (server_name, server_port, e))
        sys.exit(1)

    try:
        while True:
            try:
                line = input("ftp> ").strip()
            except EOFError:
                line = "quit"
            if not line:
                continue

            parts = line.split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1].strip() if len(parts) > 1 else ""

            try:
                if cmd == "ls":
                    cmd_ls(ctrl)
                elif cmd == "get" and arg:
                    cmd_get(ctrl, arg)
                elif cmd == "put" and arg:
                    cmd_put(ctrl, arg)
                elif cmd in ("get", "put"):
                    print("USAGE: %s <file name>" % cmd)
                elif cmd == "quit":
                    send_msg(ctrl, "quit")
                    recv_msg(ctrl)
                    break
                else:
                    print("Unknown command. Use: get <file>, put <file>, ls, quit")
            except socket.timeout:
                print("Timed out waiting for the server's data connection")
            except (ConnectionError, OSError) as e:
                print("Connection error:", e)
                break
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
