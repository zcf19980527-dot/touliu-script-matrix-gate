"""Length, hook-collision, and near-copy gates over an expanded matrix."""

from __future__ import annotations

from dataclasses import dataclass

from touliu_script_matrix.atoms import Gates
from touliu_script_matrix.expand import Script
from touliu_script_matrix.similarity import hamming, jaccard_sets, shingles, simhash


@dataclass(frozen=True)
class LengthFailure:
    name: str
    char_count: int
    reason: str


@dataclass(frozen=True)
class HookCollision:
    left_id: str
    right_id: str
    left_text: str
    right_text: str
    hamming: int
    jaccard: float


@dataclass(frozen=True)
class HookReuse:
    hook_id: str
    text: str
    count: int
    limit: int

    @property
    def over(self) -> bool:
        return self.count > self.limit


@dataclass(frozen=True)
class SimilarPair:
    left: str
    right: str
    hamming: int
    jaccard: float


@dataclass(frozen=True)
class GateReport:
    length_failures: tuple[LengthFailure, ...]
    hook_collisions: tuple[HookCollision, ...]
    hook_reuse: tuple[HookReuse, ...]
    similar_pairs: tuple[SimilarPair, ...]
    script_count: int
    pair_count: int

    @property
    def passed(self) -> bool:
        reuse_over = any(item.over for item in self.hook_reuse)
        return not (
            self.length_failures
            or self.hook_collisions
            or reuse_over
            or self.similar_pairs
        )


def evaluate(scripts: tuple[Script, ...] | list[Script], gates: Gates) -> GateReport:
    rows = tuple(scripts)
    failures = tuple(
        LengthFailure(script.name, script.char_count, reason)
        for script in rows
        if (reason := _length_reason(script.char_count, gates)) is not None
    )
    collisions, reuse = _hooks(rows, gates)
    pairs = _pairs(rows, gates)
    pair_count = len(rows) * (len(rows) - 1) // 2
    return GateReport(
        length_failures=failures,
        hook_collisions=collisions,
        hook_reuse=reuse,
        similar_pairs=pairs,
        script_count=len(rows),
        pair_count=pair_count,
    )


def _length_reason(count: int, gates: Gates) -> str | None:
    if count < gates.min_chars:
        return "short"
    if count > gates.max_chars:
        return "long"
    return None


def _hooks(
    scripts: tuple[Script, ...], gates: Gates
) -> tuple[tuple[HookCollision, ...], tuple[HookReuse, ...]]:
    order: list[str] = []
    text_by_id: dict[str, str] = {}
    counts: dict[str, int] = {}
    for script in scripts:
        counts[script.hook_id] = counts.get(script.hook_id, 0) + 1
        if script.hook_id not in text_by_id:
            text_by_id[script.hook_id] = script.hook
            order.append(script.hook_id)
    fingerprints = {
        hook_id: (
            simhash(text_by_id[hook_id], gates.shingle_n),
            shingles(text_by_id[hook_id], gates.shingle_n),
        )
        for hook_id in order
    }
    collisions: list[HookCollision] = []
    for i, left_id in enumerate(order):
        left_hash, left_grams = fingerprints[left_id]
        for right_id in order[i + 1 :]:
            right_hash, right_grams = fingerprints[right_id]
            distance = hamming(left_hash, right_hash)
            overlap = jaccard_sets(left_grams, right_grams)
            if gates.hooks_collide(distance, overlap):
                collisions.append(
                    HookCollision(
                        left_id=left_id,
                        right_id=right_id,
                        left_text=text_by_id[left_id],
                        right_text=text_by_id[right_id],
                        hamming=distance,
                        jaccard=overlap,
                    )
                )
    collisions.sort(key=lambda item: (-item.jaccard, item.hamming, item.left_id, item.right_id))
    reuse = tuple(
        HookReuse(
            hook_id=hook_id,
            text=text_by_id[hook_id],
            count=counts[hook_id],
            limit=gates.max_hook_reuse,
        )
        for hook_id in order
    )
    return tuple(collisions), reuse


def _pairs(scripts: tuple[Script, ...], gates: Gates) -> tuple[SimilarPair, ...]:
    fingerprints = [
        (
            script,
            simhash(script.spoken, gates.shingle_n),
            shingles(script.spoken, gates.shingle_n),
        )
        for script in scripts
    ]
    found: list[SimilarPair] = []
    for i, (left, left_hash, left_grams) in enumerate(fingerprints):
        for right, right_hash, right_grams in fingerprints[i + 1 :]:
            distance = hamming(left_hash, right_hash)
            overlap = jaccard_sets(left_grams, right_grams)
            if gates.pair_is_similar(distance, overlap):
                found.append(
                    SimilarPair(
                        left=left.name,
                        right=right.name,
                        hamming=distance,
                        jaccard=overlap,
                    )
                )
    found.sort(key=lambda item: (-item.jaccard, item.hamming, item.left, item.right))
    return tuple(found)
