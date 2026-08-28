"""Small reproducibility utilities shared by experiment modules."""

from __future__ import annotations

import hashlib


def derive_seed(global_seed: int, *coordinates: int) -> int:
    """Derive a stable 32-bit seed from experiment coordinates.

    This avoids Python's process-randomized ``hash`` and supports future
    repetitions without changing the generation loop.
    """

    material = ":".join(str(value) for value in (global_seed, *coordinates))
    digest = hashlib.sha256(material.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="big", signed=False)

