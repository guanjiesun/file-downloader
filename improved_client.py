import os
import time
import socket
import threading

HOST            = '127.0.0.1'   # 服务器地址
PORT            = 8888          # 服务器端口
NUM_THREADS     = 4             # 并发线程数
HTTP_VERSION    = "HTTP/1.1"    # HTTP 版本
USER_AGENT      = 'FileDownloader/1.0'
BUFFER_SIZE     = 4096
FD              = os.open("output", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

def http_request(method="GET", path="/", start=-1, end=-1):
    # 构造 HTTP 请求报文
    request_line = f"{method} {path} {HTTP_VERSION}\r\n"
    headers = [
        f"Host: {HOST}:{PORT}",
        f"User-Agent: {USER_AGENT}",
        "Connection: close",
    ]
    if method == 'GET':
        headers.append(f"Range: bytes={start}-{end}")
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
        part_size = int(headers.get("Content-Length", 0))

        if method == 'HEAD':
            # HEAD 请求, part size 就是文件大小
            return part_size 

        # 先写掉 header 后可能已经读到的 body
        offset = start
        if body:
            os.pwrite(FD, body, offset)
            offset += len(body)

        # 循环接收剩余数据
        while offset - start < part_size:
            chunk = s.recv(BUFFER_SIZE)
            if not chunk:
                break
            os.pwrite(FD, chunk, offset)
            offset += len(chunk)

def get_ranges(file_size):
    chunk_size = file_size // NUM_THREADS
    ranges = []

    for i in range(NUM_THREADS):
        start = i * chunk_size
        if i == NUM_THREADS - 1:
            end = file_size - 1
        else:
            end = (i + 1) * chunk_size - 1
        ranges.append((start, end))
    return ranges

def main():
    t_begin = time.time()

    file_size = http_request("HEAD", "/")
    print(f"File size: {file_size} bytes")
    for start, end in get_ranges(file_size):
        print(start,'\t', end)

    threads = list()
    for start, end in get_ranges(file_size):
        # 创建线程下载每个区间
        t = threading.Thread(target=http_request, args=('GET', '/', start, end))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()  # 等待所有线程完成

    # os.fsync(FD)
    os.close(FD)

    t_end = time.time()
    print(f"Download completed in {t_end - t_begin:.2f} seconds")

if __name__ == "__main__":
    main()