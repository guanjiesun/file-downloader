import time
import socket
from pathlib import Path

HOST            = '192.168.31.200'      # 服务器地址
PORT            = 8080                  # 服务器端口
HTTP_VERSION    = "HTTP/1.1"            # HTTP 版本
USER_AGENT      = 'Single-FD/0.1'       # User-Agent 头
CHUNK_SIZE      = 1024 * 16             # socket.recv 每次读取的字节数
CURR_FOLDER   = Path(__file__).parent

def http_request(method="GET", path="/leah-gotti.mp4"):
    # 构造 HTTP 请求报文
    request_line = f"{method} {path} {HTTP_VERSION}\r\n"
    headers = [
        f"Host: {HOST}:{PORT}",
        f"User-Agent: {USER_AGENT}",
        "Connection: close",
    ]
    request = request_line + "\r\n".join(headers) + "\r\n\r\n"

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        # 建立 TCP 连接并发送请求
        s.connect((HOST, PORT))
        s.sendall(request.encode())

        response = b""
        while b"\r\n\r\n" not in response:
            # 读取响应头
            chunk = s.recv(CHUNK_SIZE)
            if not chunk:
                break
            response += chunk

        # 解析响应头
        response_headers, body = response.split(b"\r\n\r\n", 1)
        print(response_headers.decode(), flush=True)
        header_lines = response_headers.decode().split("\r\n")
        _, status_code, _ = header_lines[0].split(' ', maxsplit=2)
        if status_code == '404':
            print("File not found on server.")
            return
        headers = {k: v for k, v in (line.split(": ", 1) for line in header_lines[1:])}
        file_size = int(headers.get("Content-Length", 0))

        # 文件保存在当前文件夹下
        dst_file_path = CURR_FOLDER / path.lstrip("/")
        
        # 将响应体写到文件
        with open(dst_file_path, "wb") as f:
            # 先将第一次 recv 到的数据 body 写入文件
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
    target_file = "leah-gotti.mp4"
    assert target_file, "Please specify a target file"      # target_file 不能为空
    http_request("GET", "/" + target_file)
    t_end = time.time()
    print(f"\nDownload completed in {t_end - t_begin:.4f} seconds")

if __name__ == "__main__":
    main()