"""Compatibility shim for pydub on Python 3.13+.

`pydub` falls back to importing `pyaudioop` when the stdlib `audioop`
module is unavailable. Hugging Face Spaces may still start this app on
Python 3.13 before a runtime pin takes effect, so we provide a small
drop-in subset here to keep `import gradio` working reliably.
"""

from __future__ import annotations

import array
import builtins
import math
import sys

try:  # pragma: no cover - exercised only on Python versions that still ship audioop
    from audioop import *  # type: ignore
except ImportError:
    _ARRAY_TYPES = {1: "b", 2: "h", 4: "i"}
    _MIN_VALUES = {1: -(1 << 7), 2: -(1 << 15), 4: -(1 << 31)}
    _MAX_VALUES = {1: (1 << 7) - 1, 2: (1 << 15) - 1, 4: (1 << 31) - 1}

    class error(Exception):
        """Compatibility exception matching audioop.error."""

    def _require_width(width: int) -> None:
        if width not in _ARRAY_TYPES:
            raise error(f"unsupported sample width: {width}")

    def _to_samples(fragment: bytes, width: int) -> list[int]:
        _require_width(width)
        if len(fragment) % width:
            raise error("not a whole number of frames")
        if width == 1:
            return [sample - 256 if sample > 127 else sample for sample in fragment]

        samples = array.array(_ARRAY_TYPES[width])
        samples.frombytes(fragment)
        if sys.byteorder != "little":
            samples.byteswap()
        return list(samples)

    def _from_samples(samples: list[int], width: int) -> bytes:
        _require_width(width)
        if width == 1:
            return bytes(sample & 0xFF for sample in samples)

        packed = array.array(_ARRAY_TYPES[width], samples)
        if sys.byteorder != "little":
            packed.byteswap()
        return packed.tobytes()

    def _clamp(value: int, width: int) -> int:
        return builtins.max(_MIN_VALUES[width], builtins.min(_MAX_VALUES[width], value))

    def bias(fragment: bytes, width: int, amount: int) -> bytes:
        samples = _to_samples(fragment, width)
        bits = width * 8
        offset = 1 << (bits - 1)
        modulo = 1 << bits
        shifted = [((sample + amount + offset) % modulo) - offset for sample in samples]
        return _from_samples(shifted, width)

    def lin2lin(fragment: bytes, width: int, newwidth: int) -> bytes:
        _require_width(newwidth)
        if width == newwidth:
            return bytes(fragment)

        shift = 8 * (newwidth - width)
        samples = _to_samples(fragment, width)
        if shift > 0:
            converted = [sample << shift for sample in samples]
        else:
            factor = 1 << (-shift)
            converted = [int(sample / factor) for sample in samples]
        return _from_samples([_clamp(sample, newwidth) for sample in converted], newwidth)

    def ratecv(
        fragment: bytes,
        width: int,
        nchannels: int,
        inrate: int,
        outrate: int,
        state,
        weightA: int = 1,
        weightB: int = 0,
    ):
        del state, weightA, weightB
        _require_width(width)
        if nchannels <= 0:
            raise error("nchannels must be >= 1")
        if inrate <= 0 or outrate <= 0:
            raise error("sample rate must be >= 1")

        frame_width = width * nchannels
        if len(fragment) % frame_width:
            raise error("not a whole number of frames")
        if not fragment or inrate == outrate:
            return bytes(fragment), None

        frames = [fragment[i:i + frame_width] for i in range(0, len(fragment), frame_width)]
        output_frames = builtins.max(1, int(round(len(frames) * (outrate / inrate))))
        converted = [frames[min(int(index * inrate / outrate), len(frames) - 1)] for index in range(output_frames)]
        return b"".join(converted), None

    def tostereo(fragment: bytes, width: int, lfactor: float, rfactor: float) -> bytes:
        samples = _to_samples(fragment, width)
        stereo: list[int] = []
        for sample in samples:
            stereo.append(_clamp(int(round(sample * lfactor)), width))
            stereo.append(_clamp(int(round(sample * rfactor)), width))
        return _from_samples(stereo, width)

    def tomono(fragment: bytes, width: int, lfactor: float, rfactor: float) -> bytes:
        samples = _to_samples(fragment, width)
        if len(samples) % 2:
            raise error("not a whole number of stereo frames")
        mono = []
        for index in range(0, len(samples), 2):
            sample = int(round(samples[index] * lfactor + samples[index + 1] * rfactor))
            mono.append(_clamp(sample, width))
        return _from_samples(mono, width)

    def rms(fragment: bytes, width: int) -> int:
        samples = _to_samples(fragment, width)
        if not samples:
            return 0
        return int(round(math.sqrt(sum(sample * sample for sample in samples) / len(samples))))

    def max(fragment: bytes, width: int) -> int:
        samples = _to_samples(fragment, width)
        if not samples:
            return 0
        return builtins.max(abs(sample) for sample in samples)

    def avg(fragment: bytes, width: int) -> int:
        samples = _to_samples(fragment, width)
        if not samples:
            return 0
        return int(sum(samples) / len(samples))

    def add(fragment1: bytes, fragment2: bytes, width: int) -> bytes:
        samples1 = _to_samples(fragment1, width)
        samples2 = _to_samples(fragment2, width)
        mixed = [_clamp(left + right, width) for left, right in zip(samples1, samples2)]
        return _from_samples(mixed, width)

    def mul(fragment: bytes, width: int, factor: float) -> bytes:
        samples = _to_samples(fragment, width)
        scaled = [_clamp(int(round(sample * factor)), width) for sample in samples]
        return _from_samples(scaled, width)

    def reverse(fragment: bytes, width: int) -> bytes:
        _require_width(width)
        if len(fragment) % width:
            raise error("not a whole number of frames")
        frames = [fragment[i:i + width] for i in range(0, len(fragment), width)]
        frames.reverse()
        return b"".join(frames)
