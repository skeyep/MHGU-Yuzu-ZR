"""Adapt the v0.51 Eden wheel to the shared Forge 1.5.1 plugin ABI."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import struct


def adapt(binary, fmt):
    # Keep data paths and every instruction address intact.
    nro = bytearray(binary)
    dynamic, original = fmt.table(nro)
    if 0x6FFFFEF5 in dynamic:
        raise ValueError("This wheel adapter expects a SysV symbol table.")
    expected_callbacks = {
        b"wcore_onLoad", b"wcore_onInit", b"wcore_onUpdate",
        b"wcore_onImGuiInit", b"wcore_onImGuiFreeRender",
    }
    callbacks = {row[3] for row in original if row[5] and row[3].startswith(b"wcore_on")}
    if callbacks != expected_callbacks:
        raise ValueError(f"Unexpected v0.51 callbacks: {sorted(callbacks)}")
    for _, _, offset, name, _, section in original:
        if name.startswith(b"wcore_"):
            new = b"forge_" + name[6:]
        elif not section and name.startswith(b"wg"):
            new = b"ig" + name[2:]
        elif not section and name.startswith(b"Wm"):
            new = b"Im" + name[2:]
        else:
            continue
        nro[offset:offset+len(name)] = new
    _, symbols = fmt.table(nro)
    start = dynamic[4]
    bcount, scount = struct.unpack_from("<II", nro, start)
    buckets, chains = [0] * bcount, [0] * scount
    for index, _, _, name, _, _ in symbols[1:]:
        bucket = fmt.elfhash(name) % bcount
        chains[index], buckets[bucket] = buckets[bucket], index
    struct.pack_into(f"<{bcount + scount}I", nro, start+8, *buckets, *chains)
    for index, _, _, name, _, _ in symbols[1:]:
        current = buckets[fmt.elfhash(name) % bcount]
        while current != index:
            if current == 0:
                raise ValueError(f"Symbol cannot be found in rebuilt table: {name!r}")
            current = chains[current]
    # Match the author's build-ID convention for the modified NRO.
    nro[64:96] = bytes(32)
    nro[64:96] = hashlib.sha256(nro).digest()
    return nro


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheel_nro", type=Path)
    parser.add_argument("author_format_script", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("wheel_format", args.author_format_script)
    fmt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fmt)
    args.output.write_bytes(adapt(args.wheel_nro.read_bytes(), fmt))


if __name__ == "__main__":
    main()

