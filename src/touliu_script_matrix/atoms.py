"""Load the oral-script atom file."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import yaml


class AtomsError(ValueError):
    """The atom file is missing a required field or has a bad value."""


@dataclass(frozen=True)
class Atom:
    id: str
    text: str
    label: str


@dataclass(frozen=True)
class Gates:
    """Thresholds for the length, hook, and near-copy gates.

    A script pair is a near copy when ``pair_rule`` is ``both`` and SimHash
    Hamming is at most ``simhash_hamming_max`` and Jaccard is at least
    ``jaccard_max``. ``either`` flags the pair when one of those is true.
    Hook collisions always use either metric on the hook text alone.
    """

    min_chars: int = 52
    max_chars: int = 96
    shingle_n: int = 2
    simhash_hamming_max: int = 8
    jaccard_max: float = 0.90
    pair_rule: str = "both"
    hook_hamming_max: int = 16
    hook_jaccard_max: float = 0.45
    max_hook_reuse: int = 24
    pair_list_limit: int = 20

    def pair_is_similar(self, distance: int, overlap: float) -> bool:
        ham_hit = distance <= self.simhash_hamming_max
        jac_hit = overlap >= self.jaccard_max
        if self.pair_rule == "either":
            return ham_hit or jac_hit
        return ham_hit and jac_hit

    def hooks_collide(self, distance: int, overlap: float) -> bool:
        return distance <= self.hook_hamming_max or overlap >= self.hook_jaccard_max


@dataclass(frozen=True)
class Atoms:
    product: str
    hooks: tuple[Atom, ...]
    selling_points: tuple[Atom, ...]
    audiences: tuple[Atom, ...]
    tones: tuple[Atom, ...]
    ctas: tuple[Atom, ...]
    scenes: tuple[Atom, ...]
    gates: Gates
    limit: int | None
    source: str

    @property
    def combo_count(self) -> int:
        total = 1
        for group in (
            self.tones,
            self.audiences,
            self.ctas,
            self.selling_points,
            self.scenes,
            self.hooks,
        ):
            total *= len(group)
        return total


def load_atoms(path: str | Path) -> Atoms:
    source = Path(path)
    if not source.is_file():
        raise AtomsError(f"atoms file not found: {source}")
    try:
        raw = yaml.safe_load(source.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise AtomsError(f"invalid YAML in {source}: {exc}") from exc
    if not isinstance(raw, dict):
        raise AtomsError("atoms file must be a mapping")
    product = _text(raw.get("product"), "product")
    gates = _gates(raw.get("gates"))
    limit = _limit(raw.get("limit", None))
    return Atoms(
        product=product,
        hooks=_group(raw.get("hooks"), "hooks", _hook_label),
        selling_points=_group(raw.get("selling_points"), "selling_points", _point_label),
        audiences=_group(raw.get("audiences"), "audiences", _text_label),
        tones=_group(raw.get("tones"), "tones", _text_label),
        ctas=_group(raw.get("ctas"), "ctas", _text_label),
        scenes=_group(raw.get("scenes"), "scenes", _text_label),
        gates=gates,
        limit=limit,
        source=str(source),
    )


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AtomsError(f"{field} must be a non-empty string")
    text = value.strip()
    if any(ch in text for ch in "\n\r\t"):
        raise AtomsError(f"{field} must be a single line")
    return text


def _limit(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise AtomsError("limit must be a positive integer")
    return value


def _gates(value: Any) -> Gates:
    if value is None:
        return Gates()
    if not isinstance(value, dict):
        raise AtomsError("gates must be a mapping")
    defaults = Gates()
    pair_rule = str(value.get("pair_rule", defaults.pair_rule))
    if pair_rule not in {"both", "either"}:
        raise AtomsError("gates.pair_rule must be 'both' or 'either'")
    gates = Gates(
        min_chars=_int_field(value, "min_chars", defaults.min_chars, minimum=1),
        max_chars=_int_field(value, "max_chars", defaults.max_chars, minimum=1),
        shingle_n=_int_field(value, "shingle_n", defaults.shingle_n, minimum=1),
        simhash_hamming_max=_int_field(
            value, "simhash_hamming_max", defaults.simhash_hamming_max, minimum=0
        ),
        jaccard_max=_float_field(value, "jaccard_max", defaults.jaccard_max),
        pair_rule=pair_rule,
        hook_hamming_max=_int_field(
            value, "hook_hamming_max", defaults.hook_hamming_max, minimum=0
        ),
        hook_jaccard_max=_float_field(
            value, "hook_jaccard_max", defaults.hook_jaccard_max
        ),
        max_hook_reuse=_int_field(
            value, "max_hook_reuse", defaults.max_hook_reuse, minimum=1
        ),
        pair_list_limit=_int_field(
            value, "pair_list_limit", defaults.pair_list_limit, minimum=1
        ),
    )
    if gates.max_chars < gates.min_chars:
        raise AtomsError("gates.max_chars must be >= gates.min_chars")
    if not 0.0 <= gates.jaccard_max <= 1.0:
        raise AtomsError("gates.jaccard_max must be between 0 and 1")
    if not 0.0 <= gates.hook_jaccard_max <= 1.0:
        raise AtomsError("gates.hook_jaccard_max must be between 0 and 1")
    return gates


def _int_field(raw: dict[str, Any], key: str, default: int, minimum: int) -> int:
    if key not in raw or raw[key] is None:
        return default
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise AtomsError(f"gates.{key} must be an integer")
    if value < minimum:
        raise AtomsError(f"gates.{key} must be >= {minimum}")
    return value


def _float_field(raw: dict[str, Any], key: str, default: float) -> float:
    if key not in raw or raw[key] is None:
        return default
    value = raw[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AtomsError(f"gates.{key} must be a number")
    return float(value)


def _group(
    value: Any,
    field: str,
    label_for: Callable[[str, str], str],
) -> tuple[Atom, ...]:
    if not isinstance(value, list) or not value:
        raise AtomsError(f"{field} must be a non-empty list")
    atoms: list[Atom] = []
    seen: set[str] = set()
    for index, item in enumerate(value, start=1):
        atom = _atom(item, field, index, label_for)
        if atom.id in seen:
            raise AtomsError(f"duplicate id in {field}: {atom.id}")
        seen.add(atom.id)
        atoms.append(atom)
    return tuple(atoms)


def _atom(
    item: Any,
    field: str,
    index: int,
    label_for: Callable[[str, str], str],
) -> Atom:
    if isinstance(item, str):
        text = _text(item, f"{field}[{index}]")
        atom_id = str(index)
        return Atom(atom_id, text, label_for(atom_id, text))
    if not isinstance(item, dict):
        raise AtomsError(f"{field}[{index}] must be a string or a mapping")
    atom_id = str(item.get("id", index)).strip()
    if not atom_id or any(ch in atom_id for ch in "\n\r\t"):
        raise AtomsError(f"{field}[{index}].id is empty")
    text = _text(item.get("text"), f"{field}[{index}].text")
    if "label" in item and item["label"] is not None:
        label = _text(item.get("label"), f"{field}[{index}].label")
    else:
        label = label_for(atom_id, text)
    return Atom(atom_id, text, label)


def _hook_label(atom_id: str, text: str) -> str:
    del text
    return atom_id


def _point_label(atom_id: str, text: str) -> str:
    del text
    return f"卖点{atom_id}"


def _text_label(atom_id: str, text: str) -> str:
    del atom_id
    return text
