import os
import time
import socket
import threading

HOST            = '127.0.0.1'   # 服务器地址
PORT            = 8888          # 服务器端口
HTTP_VERSION    = "HTTP/1.1"    # HTTP 版本
USER_AGENT      = 'FileDownloader/1.0'
BUFFER_SIZE     = 1024 * 16
FD              = os.open("output", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

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
            chunk = s.recv(BUFFER_SIZE)
            if not chunk:
                break
            response += chunk

        header_data, body = response.split(b"\r\n\r\n", 1)
        header_lines = header_data.decode().split("\r\n")
        status_line = header_lines[0]
        headers = {k: v for k, v in (line.split(": ", 1) for line in header_lines[1:])}
        file_size = int(headers.get("Content-Length", 0))

        # 先写掉 header 后可能已经读到的 body
        remaining = file_size
        if body:
            os.write(FD, body)
            remaining -= len(body)

        # 循环接收剩余数据
        while remaining > 0:
            chunk = s.recv(BUFFER_SIZE)
            if not chunk:
                break
            os.write(FD, chunk)
            remaining -= len(chunk)

def main():
    t_begin = time.time()

    http_request("GET", "/")
    # os.fsync(FD)
    os.close(FD)

    t_end = time.time()
    print(f"Download completed in {t_end - t_begin:.2f} seconds")

if __name__ == "__main__":
    main()