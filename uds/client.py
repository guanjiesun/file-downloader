import socket
from pathlib import Path

SERVER_ADDRESS = Path("/tmp/uds_socket")
CHUNK_SIZE = 1024 * 4

def main():
    """Unix Domain and TCP socket based Client"""
    # Create Unix Domain Socket in client side
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.connect(str(SERVER_ADDRESS))
        s.sendall(b"Hello from client")
        # TODO client.shutdown is very important, otherwise server won't get EOF and keep waiting for data
        # TODO then client and server will be deadlocked!!!
        s.shutdown(socket.SHUT_WR)  
        response = b""
        while data := s.recv(CHUNK_SIZE):
            response += data
        print(response.decode())

if __name__ == "__main__":
    main()