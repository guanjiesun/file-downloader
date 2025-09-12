### server.py
> A web server to supply files

### server-zero-copy.py
> A web server to supply files use socket.sendfiles method

### client-async.py
> Empty, not yet to implement it.

### client-improved.py
> An fast file downloader, improved based on client-bad.py (Write data to file in a streaming way)
> Using pwrite and HTTP if-range tech, pwrite is unavaiable in Windows OS

### client-portable.py
> Modified based on client-improved.py
> Using python built-in open and write method of file object, make the client avaiable on Windows OS too

### assets folder
> Create by yourself, put your files in the server side

### README and gitignore
> Self-evident

### uds folder
> Play with Unix domain socket and present a deadlock scene when Client without shutdown code"