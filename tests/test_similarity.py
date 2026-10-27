"""Stdlib SimHash and Jaccard."""

from __future__ import annotations

import hashlib

from touliu_script_matrix.similarity import (
    char_count,
    hamming,
    jaccard,
    shingles,
    simhash,
)


def test_hamming_counts_differing_bits():
    assert hamming(0, 0) == 0
    assert hamming(0b1010, 0b1111) == 2
    assert hamming(0, (1 << 64) - 1) == 64


def test_jaccard_identical_partial_and_disjoint():
    assert jaccard("护膝保暖", "护膝保暖") == 1.0
    assert jaccard("甲乙", "丙丁") == 0.0
    overlap = jaccard("护膝保暖", "护膝透气")
    assert 0.0 < overlap < 1.0
    assert shingles("膝盖", 2) == {"膝盖"}


def test_jaccard_empty_strings():
    assert jaccard("", "") == 1.0
    assert jaccard("", "膝盖") == 0.0
    assert jaccard("   ", "\n") == 1.0


def test_simhash_single_feature_is_blake2s():
    text = "膝"
    digest = hashlib.blake2s(text.encode("utf-8"), digest_size=8).digest()
    assert simhash(text, n=2) == int.from_bytes(digest, "big")


def test_simhash_is_stable_64bit_and_ignores_whitespace():
    text = "三层锁温，膝盖前后左右都包住。"
    first = simhash(text)
    assert first == simhash(text)
    assert 0 <= first < 2**64
    assert simhash("膝 盖 保 暖") == simhash("膝盖保暖")
    assert char_count("膝 盖") == 2
    assert hamming(first, simhash(text)) == 0


def test_near_duplicate_is_closer_than_unrelated():
    near_a = "三层锁温，膝盖前后左右都包住，坐着一上午也不僵。"
    near_b = "三层锁温，膝盖前后左右都包住，坐着一上午也不觉得僵。"
    far = "夏天空调直吹，后背冰凉，记得多喝温水，晚上早点睡。"
    assert hamming(simhash(near_a), simhash(near_b)) < hamming(
        simhash(near_a), simhash(far)
    )
    assert jaccard(near_a, near_b) > jaccard(near_a, far)
    assert jaccard(near_a, near_b) > 0.8
    assert jaccard(near_a, far) < 0.2
