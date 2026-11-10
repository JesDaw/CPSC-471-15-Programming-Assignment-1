# *****************************************************************
# serv.py - simplified FTP server (CPSC471 Programming Assignment 1)
#
# Usage: python3 serv.py <PORT NUMBER>
#
# One control connection per client lasts for the whole session.
# A new data connection is opened BY THE SERVER to the client for
# every ls / get / put, and closed when the transfer finishes.
# See PROTOCOL.txt for the message formats.
# *****************************************************************
import os
import socket
import sys
import threading

HEADER_LEN = 10          # every message starts with a 10-byte ASCII length
CHUNK = 65536            # file transfer chunk size
DATA_TIMEOUT = 15        # seconds to wait when connecting to client data port


# ------------------------------------------------------------------
# Reliable send / receive helpers (send()/recv() may move fewer
# bytes than requested, so we loop).
# ------------------------------------------------------------------
def recv_all(sock, num_bytes):
    """Receive exactly num_bytes. Returns fewer only if peer closed."""
    buf = bytearray()
    while len(buf) < num_bytes:
        tmp = sock.recv(min(CHUNK, num_bytes - len(buf)))
        if not tmp:
            break
        buf += tmp
    return bytes(buf)


def send_all(sock, data):
    """Send every byte of data."""
    sent = 0
    while sent < len(data):
        sent += sock.send(data[sent:])


def send_msg(sock, text):
    """Send a control message: 10-byte zero-padded length + UTF-8 text."""
    payload = text.encode("utf-8")
    send_all(sock, str(len(payload)).zfill(HEADER_LEN).encode("ascii") + payload)


def recv_msg(sock):
    """Receive one control message. Returns None if peer closed."""
    header = recv_all(sock, HEADER_LEN)
    if len(header) != HEADER_LEN:
        return None
    size = int(header)
    payload = recv_all(sock, size)
    if len(payload) != size:
        return None
    return payload.decode("utf-8")


def send_blob(sock, data):
    """Send a data-channel blob (size header + bytes)."""
    send_all(sock, str(len(data)).zfill(HEADER_LEN).encode("ascii") + data)


# ------------------------------------------------------------------
# Data channel
# ------------------------------------------------------------------
def open_data_channel(client_ip, port):
    """The server connects to the ephemeral port the client is listening on."""
    data_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data_sock.settimeout(DATA_TIMEOUT)
    data_sock.connect((client_ip, port))
    data_sock.settimeout(None)
    return data_sock


def valid_filename(name):
    """Only plain file names in the server's directory are allowed."""
    return bool(name) and name == os.path.basename(name) and name not in (".", "..")


# ------------------------------------------------------------------
# Command handlers. Each returns (success, message) for logging.
# The control-channel "ready" reply has already been decided by
# the caller; these handle the transfer and the final status.
# ------------------------------------------------------------------
def do_ls(ctrl, client_ip, port):
    listing = "\n".join(sorted(os.listdir("."))) + "\n"
    send_msg(ctrl, "OK")
    data_sock = open_data_channel(client_ip, port)
    try:
        send_blob(data_sock, listing.encode("utf-8"))
    finally:
        data_sock.close()
    return len(listing.encode("utf-8"))


def do_get(ctrl, client_ip, port, name):
    size = os.path.getsize(name)
    send_msg(ctrl, "OK")
    data_sock = open_data_channel(client_ip, port)
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
    return size


def do_put(ctrl, client_ip, port, name):
    send_msg(ctrl, "OK")
    data_sock = open_data_channel(client_ip, port)
    tmp_name = name + ".part"
    try:
        header = recv_all(data_sock, HEADER_LEN)
        if len(header) != HEADER_LEN:
            raise IOError("data connection closed before size header")
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
        os.replace(tmp_name, name)      # only expose complete files
    except Exception:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
        raise
    finally:
        data_sock.close()
    return size


# ------------------------------------------------------------------
# One thread per client session
# ------------------------------------------------------------------
def handle_client(ctrl, addr):
    client_ip = addr[0]
    print("Client connected:", addr)
    try:
        while True:
            msg = recv_msg(ctrl)
            if msg is None:
                print("Client %s disconnected unexpectedly" % (addr,))
                break

            parts = msg.split(" ", 1)
            cmd = parts[0]

            if cmd == "quit":
                send_msg(ctrl, "OK")
                print("quit: SUCCESS (%s)" % (addr,))
                break

            if cmd not in ("ls", "get", "put"):
                send_msg(ctrl, "ERR unknown command")
                print("%s: FAILURE - unknown command" % cmd)
                continue

            # Request format: "<cmd> <port>" (ls) or "<cmd> <port> <filename>"
            try:
                if cmd == "ls":
                    port, name = int(parts[1]), None
                else:
                    port_str, name = parts[1].split(" ", 1)
                    port = int(port_str)
            except (IndexError, ValueError):
                send_msg(ctrl, "ERR malformed request")
                print("%s: FAILURE - malformed request" % cmd)
                continue

            # Validate before telling the client to expect a transfer.
            if cmd in ("get", "put") and not valid_filename(name):
                send_msg(ctrl, "ERR invalid file name")
                print("%s %s: FAILURE - invalid file name" % (cmd, name))
                continue
            if cmd == "get" and not os.path.isfile(name):
                send_msg(ctrl, "ERR file not found")
                print("get %s: FAILURE - file not found" % name)
                continue

            try:
                if cmd == "ls":
                    n = do_ls(ctrl, client_ip, port)
                elif cmd == "get":
                    n = do_get(ctrl, client_ip, port, name)
                else:
                    n = do_put(ctrl, client_ip, port, name)
                send_msg(ctrl, "DONE %d" % n)
                print("%s%s: SUCCESS (%d bytes)" % (cmd, " " + name if name else "", n))
            except Exception as e:
                print("%s%s: FAILURE - %s" % (cmd, " " + name if name else "", e))
                try:
                    send_msg(ctrl, "ERR %s" % e)
                except Exception:
                    break
    except Exception as e:
        print("Session error with %s: %s" % (addr, e))
    finally:
        ctrl.close()
        print("Client session closed:", addr)


def main():
    if len(sys.argv) != 2:
        print("USAGE: python3 %s <PORT NUMBER>" % sys.argv[0])
        sys.exit(1)

    try:
        port = int(sys.argv[1])
    except ValueError:
        print("Port must be an integer")
        sys.exit(1)

    welcome = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    welcome.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    welcome.bind(("", port))
    welcome.listen(5)
    print("FTP server listening on port %d (serving %s)" % (port, os.getcwd()))

    try:
        while True:
            ctrl, addr = welcome.accept()
            threading.Thread(target=handle_client, args=(ctrl, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\nShutting down")
    finally:
        welcome.close()


if __name__ == "__main__":
    main()
