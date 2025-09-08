import time
import socket
from pathlib import Path

HOST            = '127.0.0.1'   # 服务器地址
PORT            = 8888          # 服务器端口
HTTP_VERSION    = "HTTP/1.1"    # HTTP 版本
USER_AGENT      = 'FileDownloader/1.0'
CHUNK_SIZE      = 1024 * 16     # socket.recv 每次读取的字节数

def http_request(method="GET", path="/"):
    # 构造 HTTP 请求报文
    request_line = f"{method} {path} {HTTP_VERSION}\r\n"
    headers = [
        f"Host: {HOST}:{PORT}",
        f"User-Agent: {USER_AGENT}",
        "Connection: close",
    ]
    request = request_line + "\r\n".join(headers) + "\r\n\r\n"

    # 建立 TCP 连接并发送请求
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall(request.encode())

        response = b""
        while b"\r\n\r\n" not in response:
            # 先把响应头读完
            chunk = s.recv(CHUNK_SIZE)
            if not chunk:
                break
            response += chunk

        # 解析响应头
        response_headers, body = response.split(b"\r\n\r\n", 1)
        print(response_headers.decode(), flush=True)
        header_lines = response_headers.decode().split("\r\n")
        status_line = header_lines[0]
        headers = {k: v for k, v in (line.split(": ", 1) for line in header_lines[1:])}
        file_size = int(headers.get("Content-Length", 0))
        
        # 将收到的响应体数据写到文件
        with open("output", "wb") as f:
            # 先写 header 后可能已经读到的 body
            remaining = file_size
            if body:
                f.write(body)
                remaining -= len(body)

            # 循环接收剩余数据
            while remaining > 0:
                chunk = s.recv(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)
                remaining -= len(chunk)

def main():
    t_begin = time.time()
    http_request("GET", "/")
    t_end = time.time()
    print(f"\nDownload completed in {t_end - t_begin:.4f} seconds")

if __name__ == "__main__":
    main()