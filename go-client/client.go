package main

import (
	"bufio"
	"fmt"
	"io"
	"net"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

const (
	HOST         = "192.168.31.200"
	PORT         = 8080
	HTTP_VERSION = "HTTP/1.1"
	USER_AGENT   = "Go-Client/0.1"
	CHUNK_SIZE   = 16 * 1024
)

func httpRequest(method, path string) error {
	// 构造 HTTP 请求
	request := fmt.Sprintf("%s %s %s\r\nHost: %s:%d\r\nUser-Agent: %s\r\nConnection: close\r\n\r\n",
		method, path, HTTP_VERSION, HOST, PORT, USER_AGENT)

	addr := fmt.Sprintf("%s:%d", HOST, PORT)
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		return err
	}
	defer conn.Close()

	// 发送请求, conn.Write = conn.send
	_, err = conn.Write([]byte(request))
	if err != nil {
		return err
	}

	reader := bufio.NewReader(conn)

	// 读取响应头
	responseHeaders := ""
	for {
		line, err := reader.ReadString('\n')
		if err != nil {
			return err
		}
		if line == "\r\n" {
			break
		}
		responseHeaders += line
	}

	fmt.Println("=== Response Headers ===")
	fmt.Print(responseHeaders)

	// 解析状态码
	lines := strings.Split(responseHeaders, "\r\n")
	statusParts := strings.SplitN(lines[0], " ", 3)
	if len(statusParts) < 2 {
		return fmt.Errorf("invalid response status line")
	}
	statusCode := statusParts[1]
	if statusCode == "404" {
		fmt.Println("File not found on server.")
		return nil
	}

	// 解析 Content-Length
	headersMap := make(map[string]string)
	for _, line := range lines[1:] {
		if line == "" {
			continue
		}
		parts := strings.SplitN(line, ": ", 2)
		if len(parts) == 2 {
			headersMap[parts[0]] = parts[1]
		}
	}
	fileSize := 0
	if val, ok := headersMap["Content-Length"]; ok {
		fileSize, _ = strconv.Atoi(val)
	}

	// 文件保存路径
	dstFilePath := filepath.Join(".", path[1:])
	f, err := os.Create(dstFilePath)
	if err != nil {
		return err
	}
	defer f.Close()

	// 写入响应体
	remaining := fileSize
	buf := make([]byte, CHUNK_SIZE)
	for remaining > 0 {
		n, err := reader.Read(buf)
		if err != nil && err != io.EOF {
			return err
		}
		if n == 0 {
			break
		}
		if n > remaining {
			n = remaining
		}
		f.Write(buf[:n])
		remaining -= n
	}

	fmt.Printf("\nDownload completed: %s (%d bytes)\n", dstFilePath, fileSize)
	return nil
}

func main() {
	start := time.Now()

	targetFile := "leah-gotti.mp4"
	if targetFile == "" {
		fmt.Println("Please specify a target file")
		return
	}
	err := httpRequest("GET", "/"+targetFile)
	if err != nil {
		fmt.Println("Error:", err)
	}

	fmt.Printf("Time elapsed: %.4f seconds\n", time.Since(start).Seconds())
}
