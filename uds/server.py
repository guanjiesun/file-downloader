import socket
from pathlib import Path

SERVER_ADDRESS = Path("/tmp/uds_socket")
CHUNK_SIZE = 1024

def main():
    # If the socket file already exists, remove it
    if SERVER_ADDRESS.exists():
        SERVER_ADDRESS.unlink()

    # Create Unix Domain Socket in server side
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.bind(str(SERVER_ADDRESS))
        s.listen(16)
        print(f"[*] Listening at {str(SERVER_ADDRESS)}...")

        while True:
            try:
                conn, _ = s.accept()
            except KeyboardInterrupt:
                print("\n[*] Shutting down server...")
                break
            with conn:
                request = b""
                while data := conn.recv(CHUNK_SIZE):
                    request += data

                print(f"[From client]: {request.decode()}")
                conn.sendall(b"Hello from server")
                conn.shutdown(socket.SHUT_WR)

if __name__ == "__main__":
    main()