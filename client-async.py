import os
import time
import asyncio

HOST            = '127.0.0.1'   # 服务器地址
PORT            = 8080          # 服务器端口
NUM_COROS       = 8             # 并发协程数
CHUNK_SIZE      = 1024 * 4
HTTP_VERSION    = "HTTP/1.1"
CLIENT_NAME     = 'AsyncDownloader/0.1'
TARGET_FILE     = 'leah-gotti.mp4'
FD = os.open(TARGET_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)

async def http_request(method="GET", path="/", start=-1, end=-1):
    # HTTP GET or HTTP HEAD
    method = method.upper()
    if method not in ['GET', 'HEAD']:
        raise Exception("Wrong request method, only GET and HEAD are allowed!")
    if method == 'GET' and (start == -1 or end == -1):
        raise Exception("Wrong start or end!")

    # 构造请求行和请求头
    request_line = f"{method} {path} {HTTP_VERSION}\r\n"
    headers = [
        f"Host: {HOST}:{PORT}",
        f"User-Agent: {CLIENT_NAME}",
        "Connection: close",
    ]
    if method == 'GET':
        headers.append(f"Range: bytes={start}-{end}")
    request = request_line + "\r\n".join(headers) + "\r\n\r\n"

    # 建立异步连接, 发送请求
    reader, writer = await asyncio.open_connection(HOST, PORT)
    writer.write(request.encode())
    await writer.drain()    # 相当于异步版本的 socket.sendall 方法

    # 异步接收响应
    response = b""
    while b"\r\n\r\n" not in response:
        chunk = await reader.read(CHUNK_SIZE)
        if not chunk:
            break
        response += chunk
    
    # 解析状态行响应头
    header_data, body = response.split(b"\r\n\r\n", 1)
    header_lines = header_data.decode().split("\r\n")
    status_line = header_lines[0]
    headers = {k: v for k, v in (line.split(": ", 1) for line in header_lines[1:])}
    part_size = int(headers.get("Content-Length", 0))
    if method == "GET":
        if part_size != (end-start+1):
            raise Exception("Get unexpected part size!")

    if method == "HEAD":
        return part_size

    if body:
        os.pwrite(FD, body, start)
        start += len(body)

    while start < end:
        chunk = await reader.read(CHUNK_SIZE)
        if not chunk:
            break
        os.pwrite(FD, chunk, start)
        start += len(chunk)

    writer.close()
    await writer.wait_closed()

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
    max_width = len(str(file_size))
    for start, end in ranges:
        print(f"{start:>{max_width}} --> {end:<{max_width}}")
    return ranges

async def main():
    t_begin = time.time()

    # 使用 HEAD 请求获取文件大小
    file_size = await http_request("HEAD", "/" + TARGET_FILE)
    if file_size == 0:
        raise Exception("Get file size unsucessfully!")
    print(f"file size: {file_size}", flush=True)
    ranges = get_ranges(file_size)

    coros = [http_request("GET", "/"+TARGET_FILE, start, end) for start, end in ranges]
    await asyncio.gather(*coros)        

    os.fsync(FD)
    os.close(FD)

    t_end = time.time()
    print(f"Download completed in {t_end - t_begin:.2f} seconds")

if __name__ == "__main__":
    asyncio.run(main())
