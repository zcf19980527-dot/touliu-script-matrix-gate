"""Text fingerprints using the stdlib only.

SimHash is the classic 64-bit weighted vote. Each character shingle is hashed
with ``hashlib.blake2s`` (8-byte digest). Jaccard uses the same shingles.
"""

from __future__ import annotations

import hashlib


def compact(text: str) -> str:
    """Drop whitespace. Spoken 字数 and shingles both use this form."""
    return "".join(ch for ch in text if not ch.isspace())


def char_count(text: str) -> int:
    return len(compact(text))


def shingles(text: str, n: int = 2) -> set[str]:
    """Character n-grams of the compacted text.

    Texts shorter than ``n`` contribute their whole compacted string, so a
    one-character line still has a feature.
    """
    if n < 1:
        raise ValueError("shingle n must be >= 1")
    chars = compact(text)
    if not chars:
        return set()
    if len(chars) < n:
        return {chars}
    return {chars[i : i + n] for i in range(len(chars) - n + 1)}


def jaccard(left: str, right: str, n: int = 2) -> float:
    return jaccard_sets(shingles(left, n), shingles(right, n))


def jaccard_sets(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    union = len(left | right)
    if union == 0:
        return 1.0
    return len(left & right) / union


def blake2s_u64(feature: str) -> int:
    digest = hashlib.blake2s(feature.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big", signed=False)


def simhash(text: str, n: int = 2) -> int:
    """64-bit SimHash. An empty string hashes to 0.

    One feature reproduces its blake2s integer: each set hash bit votes +1
    and each unset bit votes -1, and the sign becomes the output bit.
    """
    features = shingles(text, n)
    if not features:
        return 0
    votes = [0] * 64
    for feature in sorted(features):
        value = blake2s_u64(feature)
        for bit in range(64):
            if value & (1 << bit):
                votes[bit] += 1
            else:
                votes[bit] -= 1
    out = 0
    for bit, vote in enumerate(votes):
        if vote > 0:
            out |= 1 << bit
    return out


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()
