"""Build the RC fix1 sound requests and a dedicated GU Helm Breaker collider."""

import argparse
import ctypes
import math
from pathlib import Path
import re
import struct
import sys
import zipfile


CUES = (
    "IAI_NONE", "IAI_WHITE", "IAI_YELLOW", "IAI_RED", "HELM_SWING",
    "FORESIGHT_START", "COUNTER", "HELM_HIT", "ROUND_SWING", "ROUND_RANK",
)
PCM_LENGTHS = (0x27000, 0x2A000, 0x2A000, 0x2A000, 0x1C000,
               0x1A000, 0x1F000, 0x30000, 0x1E000, 0x12000)
BANK_PATH = r"sound\se\pl\wp\swo\world\snd_world"
WAVE_ROOT = r"sound\se\pl\wp\swo\world\wav"
WAVE_TYPE = 0x79C47B59


def read_pcm(zip_path):
    import numpy as np

    with zipfile.ZipFile(zip_path) as archive:
        plugin, = (name for name in archive.namelist()
                   if name.endswith("/mhgu_fix40_fx.nro"))
        data = archive.read(plugin)
    if data[16:20] != b"NRO0" or struct.unpack_from("<2I", data, 0x30) != (0xB1000, 0x160000):
        raise ValueError("Expected DB漫 RC fix1 ARM32 NRO")
    next_offset = 0xB7000
    for index, expected_length in enumerate(PCM_LENGTHS):
        offset, length = struct.unpack_from("<II", data, 0xB6750 + 8 * index)
        offset += 0xB6000
        if offset != next_offset or length != expected_length or offset + length > len(data):
            raise ValueError(f"Unexpected RC fix1 PCM slot {index}")
        # The RC submits interleaved stereo PCM16 at 48 kHz. GU's positional
        # bank uses mono. Average the two channels without gain or clipping.
        pcm = np.frombuffer(data, dtype="<i2", count=length // 2, offset=offset)
        yield np.rint(pcm.reshape(-1, 2).mean(axis=1)).astype(np.int16)
        next_offset = offset + length


def load_encoder(path):
    dll = ctypes.CDLL(str(path.resolve()))
    shorts = ctypes.POINTER(ctypes.c_short)
    dll.DSPCorrelateCoefs.argtypes = [shorts, ctypes.c_int, shorts]
    dll.DSPEncodeFrame.argtypes = [shorts, ctypes.c_int,
                                   ctypes.POINTER(ctypes.c_ubyte), shorts]
    dll.DSPCorrelateCoefs.restype = dll.DSPEncodeFrame.restype = None
    return dll


def make_wave(header, audio, encoder):
    from build_wilds_audio import encode
    from fix_dsp_wave_sizes import fix_wave

    payload, coefficients, snr = encode(audio, encoder)
    samples = len(audio)
    wave = bytearray(header)
    struct.pack_into("<If", wave, 8, len(payload), samples / 48000)
    struct.pack_into("<16h", wave, 24, *coefficients)
    struct.pack_into("<6I", wave, 96, samples, 48000, 0, 0, samples - 1, 0)
    result = bytes(wave) + payload + bytes(80)
    if fix_wave(result, "RC fix1") is not None:
        raise ValueError("DSP length exceeds its declaration")
    return result, snr


def append_audio(source, dest, samples, encoder, header_path):
    from build_gu_round_audio import item, pack
    from portkit import read_arc

    prefix, entries = read_arc(source)
    bank_index, = (i for i, e in enumerate(entries) if e.name == BANK_PATH and e.kind == 0x15D782FB)
    request_index, = (i for i, e in enumerate(entries) if e.name == BANK_PATH and e.kind == 0x1BCC4966)
    bank_entry, request_entry = entries[bank_index], entries[request_index]
    bank = bytearray(bank_entry.data())
    requests = request_entry.data()
    count, = struct.unpack_from("<I", requests, 8)
    bank_count, = struct.unpack_from("<I", bank, 12)
    group, = struct.unpack_from("<I", bank, 20)
    if (len(entries), count, bank_count, (group >> 17) & 1023) != (1217, 151, 143, 143):
        raise ValueError("Expected the v1.2.7 integrated audio bank")

    donor_id = 75
    first_row, row_size = 52, 132
    template = requests[first_row + donor_id * row_size:first_row + (donor_id + 1) * row_size]
    end = 32
    donor = None
    max_key = 0
    for _ in range(bank_count):
        stop = bank.index(0, end)
        row = bank[stop + 1:stop + 81]
        keys = row[75:78]
        if template[2] in keys:
            donor = row
        max_key = max(max_key, *keys)
        end = stop + 81
    if donor is None or len(bank) - end != 8 or max_key + len(CUES) >= 256:
        raise ValueError("Unexpected SBKR rows")

    wave_entry = next(e for e in entries if e.kind == WAVE_TYPE)
    wave_header = wave_entry.data()[:120]
    additions, bank_rows, request_rows = [], bytearray(), bytearray()
    for i, (cue, pcm) in enumerate(zip(CUES, samples, strict=True)):
        name = WAVE_ROOT + "\\rc114_" + cue.lower()
        wave, snr = make_wave(wave_header, pcm, encoder)
        additions.append(item(wave_entry, name, wave))
        key, request = max_key + 1 + i, count + i
        bank_row = bytearray(donor)
        bank_row[75:78] = bytes([key] * 3)
        bank_rows.extend(name.encode("ascii") + b"\0" + bank_row)
        row = bytearray(template)
        struct.pack_into("<HB", row, 0, request, key)
        row[14] = request
        request_rows.extend(row)
        print(f"{cue}: request {request}, {len(pcm)} samples, DSP SNR {snr:.1f} dB")

    bank[end:end] = bank_rows
    struct.pack_into("<I", bank, 12, bank_count + len(CUES))
    struct.pack_into("<I", bank, 20, (group & ~(1023 << 17)) | ((bank_count + len(CUES)) << 17))
    new_header = bytearray(requests[:first_row])
    struct.pack_into("<I", new_header, 8, count + len(CUES))
    for field in (32, 36, 40, 44, 48):
        pointer, = struct.unpack_from("<I", requests, field)
        struct.pack_into("<I", new_header, field, pointer + len(request_rows))
    end = first_row + count * row_size
    footer = bytearray(requests[end:])
    path_offset, = struct.unpack_from("<I", footer)
    if not requests[path_offset:].startswith(BANK_PATH.encode("ascii") + b"\0"):
        raise ValueError("Unexpected SRQR footer")
    struct.pack_into("<I", footer, 0, path_offset + len(request_rows))
    entries[bank_index] = item(bank_entry, BANK_PATH, bank)
    entries[request_index] = item(request_entry, BANK_PATH,
                                  new_header + requests[first_row:end] + request_rows + footer)
    entries[bank_index:bank_index] = additions
    pack(prefix, entries, dest)

    header = header_path.read_text(encoding="utf-8")
    match = re.search(r"(gu_round_request_index\[256\]=\{\n)([^}]+)(\};)", header)
    if match is None or "#define GU_ROUND_RESOURCE_COUNT 1217u" not in header:
        raise ValueError("Expected v1.2.7 roundslash resource indexes")
    indexes = [int(value) for value in re.findall(r"\d+", match[2])]
    indexes = [i + len(CUES) if i >= bank_index else i for i in indexes]
    table = "".join(",".join(map(str, indexes[i:i + 16])) + ",\n" for i in range(0, 256, 16))
    header = header[:match.start(2)] + table + header[match.end(2):]
    constants = "\n".join(f"#define RC114_{cue} {count + i}u" for i, cue in enumerate(CUES))
    header = header.replace("#define GU_ROUND_RESOURCE_COUNT 1217u",
                            f"#define GU_ROUND_RESOURCE_COUNT {len(entries)}u\n{constants}")
    return header


def add_helm_shape(data):
    count, = struct.unpack_from("<I", data, 8)
    if data[:4] != b"HTS\0" or count != 18:
        raise ValueError("Expected GU v1.2.7 hitsize with 18 groups")
    groups = []
    for i in range(count):
        records, offset = struct.unpack_from("<II", data, 16 + i * 8)
        groups.append(data[offset:offset + records * 48])
    helm = bytearray(groups[5])
    if len(helm) != 6 * 48 or struct.unpack_from("<II", helm, 0) != (524296, 65537):
        raise ValueError("Unexpected GU posed Helm Breaker shape")
    radius, = struct.unpack_from("<f", helm, 12)
    start = struct.unpack_from("<3f", helm, 16)
    tip = struct.unpack_from("<3f", helm, 32)
    if radius != 65 or struct.unpack_from("<3f", helm, 4 * 48 + 16) != tip:
        raise ValueError("Unexpected GU Helm Breaker capsule endpoints")
    # Adapt the RC's 32-unit reach increase along the Wilds port blade axis.
    # Keep the original radius and move the attached tip sphere with the tip.
    delta = tuple(end - begin for begin, end in zip(start, tip))
    tip = tuple(end + 32 * axis / math.hypot(*delta) for end, axis in zip(tip, delta))
    struct.pack_into("<3f", helm, 32, *tip)
    struct.pack_into("<3f", helm, 4 * 48 + 16, *tip)
    groups.append(helm)

    rebuilt = bytearray(data[:16] + bytes(8 * len(groups)))
    struct.pack_into("<I", rebuilt, 8, len(groups))
    for i, group in enumerate(groups):
        struct.pack_into("<II", rebuilt, 16 + i * 8, len(group) // 48, len(rebuilt))
        rebuilt.extend(group)
    return bytes(rebuilt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("rc_zip", type=Path)
    parser.add_argument("base_arc_root", type=Path)
    parser.add_argument("output_arc_root", type=Path)
    parser.add_argument("wilds_tools", type=Path)
    parser.add_argument("dsp_encoder", type=Path)
    parser.add_argument("base_audio_header", type=Path)
    parser.add_argument("output_audio_header", type=Path)
    args = parser.parse_args()
    sys.path.insert(0, str(args.wilds_tools.resolve()))
    from portkit import arc_replace, read_arc

    world_audio = Path("forge/world_audio.arc")
    w07 = Path("player/quest/w07.arc")
    for path in (world_audio, w07):
        (args.output_arc_root / path).parent.mkdir(parents=True, exist_ok=True)
    header = append_audio(args.base_arc_root / world_audio, args.output_arc_root / world_audio,
                          read_pcm(args.rc_zip), load_encoder(args.dsp_encoder), args.base_audio_header)
    motion = args.base_arc_root / w07
    hitsize, = (entry for entry in read_arc(motion)[1] if entry.name.endswith("pl_we07_hitsize"))
    arc_replace(motion, args.output_arc_root / w07, {hitsize.name: add_helm_shape(hitsize.data())})
    args.output_audio_header.write_text(header, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
    
