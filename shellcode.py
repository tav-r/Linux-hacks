"""
Execute base64 encoded shellcode given as as a command line argument.
"""

from ctypes import (CDLL, CFUNCTYPE, c_char_p, c_void_p, cast, c_int, c_size_t,
                    c_char, get_errno, addressof, POINTER)
from os import strerror, fork, environ
from sys import argv, exit as sys_exit
from typing import Optional


def call_shellcode(shellcode_str: Optional[bytes] = None):
    """
    Execute given shellcode (or a simple 'Hello world!' shellcode if none was
    specified.

    Args:
        shellcode (Optional[bytes]): shellcode to execute
    """

    if not shellcode_str:
        shellcode_str = b"\xeb\x22\x5e\x48\31\xff\x66\xbf\x01\x00\x48\x31\xc0"\
                        b"\xb0\x01\x48\x31\xd2\xb2\x0d\x0f\x05\x48\x31\xc0"\
                        b"\xb0\x3c\x48\x31\xd2\xb2\x01\xfe\xca\x0f\x05\xe8"\
                        b"\xd9\xff\xff\xffHello world!\x0a\x00"

    # make page that stores the shellcode executable
    shellcode = addressof(cast(c_char_p(shellcode_str), POINTER(c_char))
                          .contents)
    pagesize = 0x1000
    page_start = shellcode - (shellcode % pagesize)  # page-align address
    if CDLL("libc.so.6", use_errno=True).mprotect(
        c_void_p(page_start), c_size_t(pagesize), c_int(7)
    ):
        sys_exit(f"Error calling mprotect(): {strerror(get_errno())}")

    # 'cast' shellcode to a function and run it
    shellcode_function = CFUNCTYPE(None)(shellcode)

    if environ.get("FORK") and fork():
        sys_exit()

    shellcode_function()


if __name__ == "__main__":
    import base64

    call_shellcode(base64.b64decode(argv[1]) if len(argv) > 1 else None)
