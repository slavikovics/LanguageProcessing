from __future__ import annotations

import struct

_STREAMING_SIZE_SENTINEL = 0xFFFFFFFF
"""RIFF/data chunk sizes when the total length isn't known upfront (streamed
generation) — players read until EOF for the data chunk regardless."""


def build_wav_header(
    *, sample_rate: int, channels: int, bits_per_sample: int, data_size: int | None = None
) -> bytes:
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    size = _STREAMING_SIZE_SENTINEL if data_size is None else data_size
    riff_size = _STREAMING_SIZE_SENTINEL if data_size is None else 36 + data_size

    header = b"RIFF" + struct.pack("<I", riff_size) + b"WAVE"
    header += b"fmt " + struct.pack(
        "<IHHIIHH", 16, 1, channels, sample_rate, byte_rate, block_align, bits_per_sample
    )
    header += b"data" + struct.pack("<I", size)
    return header
