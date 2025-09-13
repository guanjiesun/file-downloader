PROTO = "mongodb"
USER = "miller"
PASSWD = "12345678"
HOST = "localhost"
PORT = 27017
DB = "file-downloader"
COLLECTION = "record"

mongo_url = f"{PROTO}://{USER}:{PASSWD}@{HOST}:{PORT}/{DB}"
document = {
    "method": "default-method",
    "path": "default-path",
    "version": "default-version",
    "created_at": "default-time"
}