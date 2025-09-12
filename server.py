import socket
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

HOST                = '0.0.0.0'             # 主机地址
PORT                = 8080                  # 监听端口
CHUNK_SIZE          = 1024 * 4              # 每次读取文件的块大小jjj
HTTP_VERSION        = "HTTP/1.1"            # HTTP 版本
MAX_HEADER_SIZE     = 1024 * 8              # 最大请求头长度
ASSETS_PATH         = Path(__file__).parent / "assets"

def build_head_response(range_header=None, file_size=0):
    """生成 HEAD 响应, 只返回响应行 + 响应头, 不包含 body"""
    if range_header:
        _, range_value = range_header.split(":", 1)
        range_value = range_value.strip()
        if range_value.startswith("bytes="):
            range_value = range_value[len("bytes="):]
            start, end = range_value.split("-")
            start = int(start) if start else 0
            end = int(end) if end else file_size - 1
            if end >= file_size:
                end = file_size - 1
            length = end - start + 1
            status_line = "HTTP/1.1 206 Partial Content\r\n"
            headers = f"Content-Range: bytes {start}-{end}/{file_size}\r\n"
            headers += f"Content-Length: {length}\r\n"
        else:
            status_line = "HTTP/1.1 416 Range Not Satisfiable\r\n"
            headers = f"Content-Range: bytes */{file_size}\r\n"
    else:
        status_line = "HTTP/1.1 200 OK\r\n"
        headers = f"Content-Length: {file_size}\r\n"

    return (status_line + headers + "\r\n").encode()

def handle_client(conn, addr):
    """ Handle request from client """
    data = b""
    while b"\r\n\r\n" not in data:
        # obtain reqeust line and request headers first
        chunk = conn.recv(CHUNK_SIZE)
        if not chunk:
            break
        data += chunk
        if len(data) > MAX_HEADER_SIZE:
            # make sure the length of header is not great than MAX_HEADER_SIZE
            print(f"Request too large from {addr}")
            response = "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n"
            conn.sendall(response.encode())
            conn.close()
            return

    # 这里默认用户发来的请求是合法的 HTTP 请求, 且请求体是空的(只接受GET or HEAD)
    request = data.decode("utf-8", errors="ignore")
    request_line = request.split("\r\n")[0]
    print(f"=== Request From [{addr[0]}:{addr[1]}] ===\n{request}", flush=True)

    # parse request, obtain request line and request headers
    method, path, http_version = request_line.split(" ", maxsplit=2)
    method = method.upper()
    file_path = ASSETS_PATH / path.lstrip("/")

    # validate request
    if path == "/":
        # path is illegal, return 403
        response = "HTTP/1.1 403 Forbidden\r\n\r\n"
        conn.sendall(response.encode())
        conn.close()
        return
    if not file_path.exists():
        # File not found, return 404
        response = "HTTP/1.1 404 Not Found\r\n\r\n"
        conn.sendall(response.encode())
        conn.close()
        return
    if method not in ("GET", "HEAD"):
        # Method not allowed, return 405 (Only HEAD and HEAD are allowed)
        response = "HTTP/1.1 405 Method Not Allowed\r\n\r\n"
        conn.sendall(response.encode())
        conn.close()
        return
    if http_version != HTTP_VERSION:
        # Only HTTP/1.1 is supported
        response = "HTTP/1.1 505 HTTP Version Not Supported\r\n\r\n"
        conn.sendall(response.encode())
        conn.close()
        return

    file_size = file_path.stat().st_size
    range_header = None

    # 获取 Range header
    for line in request.split("\r\n"):
        if line.startswith("Range:"):
            range_header = line
            break
    
    if method == "HEAD":
        response = build_head_response(range_header, file_size)
        conn.sendall(response)
        conn.close()
        return

    if range_header:
        # Range header 存在，处理部分内容请求
        _, range_value = range_header.split(":", 1)
        range_value = range_value.strip()
        if range_value.startswith("bytes="):
            range_value = range_value[len("bytes="):]
            start, end = range_value.split("-")
            start = int(start) if start else 0
            end = int(end) if end else file_size - 1

            if end >= file_size:
                end = file_size - 1

            length = end - start + 1

            status_line = "HTTP/1.1 206 Partial Content\r\n"
            headers  = f"Content-Range: bytes {start}-{end}/{file_size}\r\n"
            headers += f"Content-Length: {length}\r\n"
            headers += "\r\n"
            # 先把响应头 + 状态行发送出去
            conn.sendall((status_line + headers).encode())

            # 再发送文件内容 (响应体)
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    conn.sendall(chunk)
                    remaining -= len(chunk)
        else:
            status_line = "HTTP/1.1 416 Range Not Satisfiable\r\n"
            headers  = f"Content-Range: bytes */{file_size}\r\n"
            headers += "\r\n"
            conn.sendall((status_line + headers).encode())
    else:
        # 没有 Range header，返回整个文件
        status_line = "HTTP/1.1 200 OK\r\n"
        headers  = f"Content-Length: {file_size}\r\n"
        headers += "\r\n"
        conn.sendall((status_line + headers).encode())
        remaining = file_size
        with open(file_path, "rb") as f:
            while remaining > 0:
                chunk = f.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                conn.sendall(chunk)
                remaining -= len(chunk)

    conn.close()

def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # Server side: socket() -> bind() -> listen() -> accept()
        # Client side: socket() -> connnect()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(16)
        print(f"\nServing on {HOST}:{PORT}\n")
        with ThreadPoolExecutor(max_workers=8) as executor:
            try:
                while True:
                    conn, addr = s.accept()
                    executor.submit(handle_client, conn, addr)
            except KeyboardInterrupt:
                print("\nServer exited")

if __name__ == "__main__":
    run_server()
