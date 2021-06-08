from ctypes import CDLL, get_errno, c_void_p
from os import fork, waitpid, execv, strerror, WIFSTOPPED
from sys import argv, exit as sys_exit
from struct import unpack


PTRACE_TRACEME = 0
PTRACE_PEEKTEXT = 1
PTRACE_POKETEXT = 4
PTRACE_DETACH = 17
PAGESIZE = 4096
LIBC = CDLL("libc.so.6", use_errno=True)

def load_and_attach(path: str, args: list[str], shellcode: bytes):
    def parse_maps_line(line: str) -> tuple[tuple[int, int], int, int]:
        addrs, perms_str, offset_str, *_ = line.split(" ")

        offset = int(offset_str, base=16)

        perms = 0
        if "r" in perms_str: perms += 4
        if "w" in perms_str: perms += 2
        if "x" in perms_str: perms += 1

        start, end = [int(addr, base=16) for addr in addrs.split("-")]

        return (start, end), perms, offset

    pid = fork()

    if not pid:
        if LIBC.ptrace(PTRACE_TRACEME, 0, 0, 0):
            sys_exit(strerror(get_errno()))

        execv(path, [path] + args)

    while True:
        _, status = waitpid(pid, 0)
        if WIFSTOPPED(status):
            break

    # find entry point
    with open(f"/proc/{pid}/maps", "r") as maps:
            addrs = [parse_maps_line(line) for line in maps.readlines()
                     if line.strip().endswith(path)]

    # first entry (start address) of first element (start and end address)
    # of first segment is the image base for the ELF executed.
    image_base = addrs[0][0][0]

    # the entry point of the binary is at offset 24
    entry_point_offset = LIBC.ptrace(PTRACE_PEEKTEXT, pid, c_void_p(image_base + 24), 0)
    if entry_point_offset == -1:
        sys_exit(f"Error calling ptrace: {strerror(get_errno())}")
    entry_point = image_base + entry_point_offset
        
    # replace instructions at entry point with shellcode
    shellcode += b"\x00" * (8 - len(shellcode) % 8)
    for i, word in enumerate(unpack(f"<{len(shellcode)//8}Q", shellcode)):
        if LIBC.ptrace(PTRACE_POKETEXT, pid, c_void_p(entry_point + i * 8), c_void_p(word)):
            sys_exit(f"Error calling ptrace: {strerror(get_errno())}")

    # detach/continue
    if LIBC.ptrace(PTRACE_DETACH, pid, 0, 0):
        sys_exit(f"Error calling ptrace: {strerror(get_errno())}")


if __name__ == "__main__":
    import base64
    load_and_attach(argv[1], argv[2:-1], base64.b64decode(argv[-1]))