import os
import socket
from concurrent.futures import ThreadPoolExecutor

HOST        = '0.0.0.0'             # 本地回环
PORT        = 8888                  # 监听端口
CHUNK_SIZE  = 1024 * 16             # 每次读取文件的块大小
# FILE_PATH   = "./assets/file.txt"                         # 返回给客户端的文件 
FILE_PATH   = "./assets/Leah Gotti_Wet Wild And Hot.mp4"  # 返回给客户端的文件
# FILE_PATH   = "./assets/4K.mp4"     # 返回给客户端的文件

def build_head_response(range_header=None):
    """生成 HEAD 响应, 只返回响应行 + 响应头, 不包含 body"""
    if not os.path.exists(FILE_PATH):
        return "HTTP/1.1 404 Not Found\r\n\r\n".encode()

    file_size = os.path.getsize(FILE_PATH)
    status_line = "HTTP/1.1 200 OK\r\n"
    headers = ""

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
            headers += f"Content-Range: bytes {start}-{end}/{file_size}\r\n"
            headers += f"Content-Length: {length}\r\n"
        else:
            status_line = "HTTP/1.1 416 Range Not Satisfiable\r\n"
            headers += f"Content-Range: bytes */{file_size}\r\n"
    else:
        headers += f"Content-Length: {file_size}\r\n"

    # headers += "Content-Type: text/plain\r\n"
    response = (status_line + headers + "\r\n").encode()
    return response

def handle_client(conn, addr):
    # 处理客户端请求
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(CHUNK_SIZE)
        if not chunk:
            break
        data += chunk
    request = data.decode("utf-8", errors="ignore")
    print("=== 请求报文 ===")
    print(request)

    # 默认返回整个文件
    status_line = "HTTP/1.1 200 OK\r\n"
    headers = ""
    # headers += "Content-Type: text/plain\r\n"
    body = b""

    method, path, version = request.split(" ", 2)
    method = method.upper()

    if not os.path.exists(FILE_PATH):
        # 文件不存在，返回 404
        response = "HTTP/1.1 404 Not Found\r\n\r\nFile not found"
        conn.sendall(response.encode())
        conn.close()
        return

    file_size = os.path.getsize(FILE_PATH)
    range_header = None

    # 获取 Range header
    for line in request.split("\r\n"):
        if line.startswith("Range:"):
            range_header = line
            break
    
    if method == "HEAD":
        response = build_head_response(range_header)
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
            headers += f"Content-Range: bytes {start}-{end}/{file_size}\r\n"
            headers += f"Content-Length: {length}\r\n"
            headers += "\r\n"
            # 先把响应头发送出去
            conn.sendall((status_line + headers).encode())

            with open(FILE_PATH, "rb") as f:
                f.seek(start)
                remaining = end - start + 1
                while remaining > 0:
                    chunk = f.read(min(CHUNK_SIZE, remaining))
                    if not chunk:
                        break
                    conn.sendall(chunk)
                    remaining -= len(chunk)
        else:
            status_line = "HTTP/1.1 416 Range Not Satisfiable\r\n"
            headers += f"Content-Range: bytes */{file_size}\r\n"
            headers += "\r\n"
            conn.sendall((status_line + headers).encode())
    else:
        # 没有 Range header，返回整个文件
        headers += f"Content-Length: {file_size}\r\n"
        headers += "\r\n"
        conn.sendall((status_line + headers).encode())
        remaining = file_size
        with open(FILE_PATH, "rb") as f:
            while remaining > 0:
                chunk = f.read(min(CHUNK_SIZE, remaining))
                if not chunk:
                    break
                conn.sendall(chunk)
                remaining -= len(chunk)

    conn.close()


def run_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen(16)
        print(f"Serving on {HOST}:{PORT}")
        with ThreadPoolExecutor(max_workers=8) as executor:
            while True:
                conn, addr = s.accept()
                executor.submit(handle_client, conn, addr)

if __name__ == "__main__":
    run_server()
