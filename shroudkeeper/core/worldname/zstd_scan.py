from __future__ import annotations

import zstandard

_ZSTD_MAGIC = b"\x28\xB5\x2F\xFD"


def find_magic_offsets(raw: bytes) -> list[int]:
    offsets: list[int] = []
    start = 0
    while True:
        position = raw.find(_ZSTD_MAGIC, start)
        if position == -1:
            break
        offsets.append(position)
        start = position + 1
    return offsets


def try_decompress_from_offset(raw: bytes, offset: int, max_output_size: int) -> bytes | None:
    if offset < 0 or offset >= len(raw):
        return None

    try:
        decompressor = zstandard.ZstdDecompressor()
        return decompressor.decompress(raw[offset:], max_output_size=max_output_size)
    except Exception:
        return None
