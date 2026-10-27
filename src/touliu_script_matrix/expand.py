"""Cartesian expansion of atoms into numbered 15-second oral scripts."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import islice, product

from touliu_script_matrix.atoms import Atom, Atoms
from touliu_script_matrix.similarity import char_count


@dataclass(frozen=True)
class Script:
    index: int
    name: str
    product: str
    hook_id: str
    hook: str
    selling_point_id: str
    selling_point_label: str
    selling_point: str
    audience: str
    tone: str
    scene_label: str
    scene: str
    cta: str
    part_hook: str
    part_body: str
    part_cta: str
    script: str
    spoken: str
    char_count: int


@dataclass(frozen=True)
class ExpandResult:
    scripts: tuple[Script, ...]
    total_combos: int
    limit: int | None

    @property
    def truncated(self) -> bool:
        return len(self.scripts) < self.total_combos


def expand(atoms: Atoms, limit: int | None = None) -> ExpandResult:
    """Expand in a stable order.

    Slowest dimension first: tones, audiences, ctas, selling points, scenes.
    Hooks vary fastest, so a small ``limit`` still covers every hook, then
    every scene, then the selling points listed first in the file.
    """
    cap = atoms.limit if limit is None else limit
    if cap is not None and cap < 1:
        raise ValueError("limit must be a positive integer")
    dims = (
        atoms.tones,
        atoms.audiences,
        atoms.ctas,
        atoms.selling_points,
        atoms.scenes,
        atoms.hooks,
    )
    total = atoms.combo_count
    stream = product(*dims)
    if cap is not None:
        stream = islice(stream, cap)
    scripts = tuple(
        _render(index, combo, atoms.product)
        for index, combo in enumerate(stream, start=1)
    )
    return ExpandResult(scripts=scripts, total_combos=total, limit=cap)


def _render(
    index: int,
    combo: tuple[Atom, Atom, Atom, Atom, Atom, Atom],
    product: str,
) -> Script:
    tone, audience, cta, point, scene, hook = combo
    part_hook = hook.text
    part_body = f"{audience.text}在{scene.text}，{tone.text}{point.text}"
    part_cta = cta.text
    spoken = f"{part_hook}{part_body}{part_cta}"
    script = f"前3s钩子：{part_hook}\n中10s卖点：{part_body}\n尾2s CTA：{part_cta}"
    name = f"{product}_{point.label}_{scene.label}_{index:03d}"
    return Script(
        index=index,
        name=name,
        product=product,
        hook_id=hook.id,
        hook=hook.text,
        selling_point_id=point.id,
        selling_point_label=point.label,
        selling_point=point.text,
        audience=audience.text,
        tone=tone.text,
        scene_label=scene.label,
        scene=scene.text,
        cta=cta.text,
        part_hook=part_hook,
        part_body=part_body,
        part_cta=part_cta,
        script=script,
        spoken=spoken,
        char_count=char_count(spoken),
    )
