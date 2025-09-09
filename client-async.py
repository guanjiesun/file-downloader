import os
import time
import socket
import asyncio

HOST = '127.0.0.1'   # 服务器地址
PORT = 8888          # 服务器端口
NUM_COROS = 8        # 并发协程数
HTTP_VERSION = "HTTP/1.1"
CLIENT_NAME = 'FileDownloader/1.0'
FD = os.open("output", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

async def http_request(method="GET", path="/", range_header=None):
    # 构造 HTTP GET / HEAD 请求报文
    method = method.upper()
    request_line = f"{method} {path} {HTTP_VERSION}\r\n"
    headers = [
        f"Host: {HOST}:{PORT}",
        f"User-Agent: {CLIENT_NAME}",
        "Connection: close",
    ]
    if range_header:
        headers.append(f"Range: {range_header}")
    request = request_line + "\r\n".join(headers) + "\r\n\r\n"

    # 用 asyncio.open_connection 建立异步连接
    reader, writer = await asyncio.open_connection(HOST, PORT)

    # 发送请求
    writer.write(request.encode())
    await writer.drain()

    # 异步接收响应
    response = b""
    while True:
        chunk = await reader.read(4096)
        if not chunk:
            break
        response += chunk

    writer.close()
    await writer.wait_closed()

    return response

def parse_response(response_bytes):
    # 把响应转成字符串，方便查找头和体的分隔符
    response_str = response_bytes.decode(errors="ignore")
    
    # 找到 header 和 body 的分隔符
    sep = response_str.find("\r\n\r\n")
    if sep == -1:
        return None, None           # 没有找到分隔符，说明响应有问题
    headers = response_str[:sep]
    body = response_bytes[sep+4:]   # 注意这里用原始的 bytes 截取 body
    return headers, body

async def get_file_size():
    """利用 HEAD 请求获取文件大小"""
    resp = await http_request("HEAD", "/")
    headers, _ = parse_response(resp)
    content_length_header = None
    for line in headers.split("\r\n"):
        if line.startswith("Content-Length"):
            content_length_header = line
            break
    if content_length_header:
        _, length = content_length_header.split(":", 1)
        return int(length.strip())
    return -1  # 获取失败

def get_ranges(file_size):
    chunk_size = file_size // NUM_COROS
    ranges = []

    for i in range(NUM_COROS):
        start = i * chunk_size
        if i == NUM_COROS - 1:
            end = file_size - 1
        else:
            end = (i + 1) * chunk_size - 1
        ranges.append((start, end))
    return ranges

async def worker(start, end):
    range_header_content = f"bytes={start}-{end}"
    resp = await http_request("GET", "/", range_header_content)
    _, body = parse_response(resp)
    os.pwrite(FD, body, start)

async def main():
    t_begin = time.time()

    file_size = await get_file_size()
    print(f"file size: {file_size}")
    ranges = get_ranges(file_size)
    print("Download ranges:", ranges)
    coros = list()
    for start, end in ranges:
        # 创建协程下载每个区间
        coro = worker(start, end)
        coros.append(coro)
    await asyncio.gather(*coros)        
    os.fsync(FD)
    os.close(FD)

    t_end = time.time()
    print(f"Download completed in {t_end - t_begin:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
