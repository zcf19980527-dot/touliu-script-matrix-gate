"""Atom loading, expansion, and the three gates."""

from __future__ import annotations

from dataclasses import replace

import pytest

from tests.conftest import ATOMS
from touliu_script_matrix import __version__
from touliu_script_matrix.atoms import AtomsError, Gates, load_atoms
from touliu_script_matrix.expand import Script, expand
from touliu_script_matrix.gates import evaluate


def _write(path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _mini() -> str:
    return """
product: 测试品
hooks:
  - {id: h1, text: "钩子甲乙丙丁"}
  - {id: h2, text: "另一句开场白"}
selling_points:
  - {id: "01", label: 卖点01, text: "卖点写得具体一点"}
audiences:
  - {id: a, text: "中老年朋友"}
tones:
  - {id: t, text: "说句实在的，"}
ctas:
  - {id: c, text: "点下方看尺码。"}
scenes:
  - {id: s1, label: 办公室, text: 办公室久坐}
  - {id: s2, label: 公园, text: 公园散步}
"""


def _script(name: str, hook_id: str, hook: str, body: str, point: str = "卖点05") -> Script:
    spoken = f"{hook}{body}点下方。"
    return Script(
        index=1,
        name=name,
        product="测试品",
        hook_id=hook_id,
        hook=hook,
        selling_point_id="05",
        selling_point_label=point,
        selling_point=body,
        audience="中老年朋友",
        tone="说句实在的，",
        scene_label="办公室",
        scene="办公室久坐",
        cta="点下方。",
        part_hook=hook,
        part_body=body,
        part_cta="点下方。",
        script=f"前3s钩子：{hook}\n中10s卖点：{body}\n尾2s CTA：点下方。",
        spoken=spoken,
        char_count=len("".join(spoken.split())),
    )


def test_example_atoms_shape_and_names():
    atoms = load_atoms(ATOMS)
    assert __version__ == "0.1.0"
    assert atoms.product == "保暖护膝"
    assert atoms.limit == 60
    assert atoms.combo_count == 480
    assert [hook.id for hook in atoms.hooks] == ["h01", "h02", "h03", "h04"]
    assert atoms.selling_points[0].label == "卖点05"
    expanded = expand(atoms)
    assert expanded.truncated
    assert len(expanded.scripts) == 60
    assert expanded.total_combos == 480
    first = expanded.scripts[0]
    last = expanded.scripts[-1]
    assert first.name == "保暖护膝_卖点05_办公室_001"
    assert last.name == "保暖护膝_卖点08_公园_060"
    assert first.hook_id == "h01"
    assert last.selling_point_label == "卖点08"
    assert last.scene_label == "公园"


def test_script_has_three_beats_and_char_count():
    script = expand(load_atoms(ATOMS)).scripts[0]
    assert script.script.splitlines() == [
        f"前3s钩子：{script.part_hook}",
        f"中10s卖点：{script.part_body}",
        f"尾2s CTA：{script.part_cta}",
    ]
    assert script.spoken == f"{script.part_hook}{script.part_body}{script.part_cta}"
    assert "前3s" not in script.spoken
    assert script.char_count == len(script.spoken)
    assert script.part_body.startswith("中老年朋友在办公室久坐，")


def test_limit_override_and_full_cartesian(tmp_path):
    path = tmp_path / "atoms.yaml"
    _write(path, _mini())
    atoms = load_atoms(path)
    assert atoms.limit is None
    full = expand(atoms)
    assert full.total_combos == 4
    assert [script.name for script in full.scripts] == [
        "测试品_卖点01_办公室_001",
        "测试品_卖点01_办公室_002",
        "测试品_卖点01_公园_003",
        "测试品_卖点01_公园_004",
    ]
    assert [script.hook_id for script in full.scripts] == ["h1", "h2", "h1", "h2"]
    capped = expand(atoms, limit=2)
    assert len(capped.scripts) == 2
    assert capped.total_combos == 4
    assert capped.truncated
    assert capped.scripts[1].scene_label == "办公室"


def test_reject_bad_atoms(tmp_path):
    with pytest.raises(AtomsError, match="not found"):
        load_atoms(tmp_path / "missing.yaml")

    empty = tmp_path / "empty.yaml"
    _write(empty, "product: 测试品\nhooks: []\n")
    with pytest.raises(AtomsError, match="hooks"):
        load_atoms(empty)

    dup = tmp_path / "dup.yaml"
    _write(
        dup,
        """
product: 测试品
hooks:
  - {id: h1, text: "钩子甲乙丙丁"}
  - {id: h1, text: "另一句开场白"}
selling_points:
  - {id: "01", text: "卖点写得具体一点"}
audiences: ["中老年朋友"]
tones: ["说句实在的，"]
ctas: ["点下方看尺码。"]
scenes: ["办公室久坐"]
""",
    )
    with pytest.raises(AtomsError, match="duplicate"):
        load_atoms(dup)

    bad = tmp_path / "bad.yaml"
    _write(
        bad,
        _mini()
        + """
gates:
  pair_rule: maybe
""",
    )
    with pytest.raises(AtomsError, match="pair_rule"):
        load_atoms(bad)

    low = tmp_path / "low.yaml"
    _write(low, "product: 测试品\nlimit: 0\n" + _mini())
    with pytest.raises(AtomsError, match="limit"):
        load_atoms(low)


def test_length_gate_short_and_long():
    gates = Gates(min_chars=52, max_chars=96, max_hook_reuse=5)
    short = _script("短", "h1", "短钩子啊", "轻")
    ok = _script("正", "h2", "正常钩子一句", "三" * 60)
    long = _script("长", "h3", "长钩子啊", "长" * 120)
    assert short.char_count < 52
    assert 52 <= ok.char_count <= 96
    assert long.char_count > 96
    report = evaluate((short, ok, long), gates)
    reasons = {item.name: item.reason for item in report.length_failures}
    assert reasons == {"短": "short", "长": "long"}
    edge_low = _script("边低", "h4", "边", "字" * 50)
    edge_high = _script("边高", "h5", "边", "字" * 94)
    # spoken adds the hook and the CTA, so rebuild exact counts via replace.
    edge_low = replace(edge_low, char_count=52, spoken="字" * 52)
    edge_high = replace(edge_high, char_count=96, spoken="字" * 96)
    under = replace(edge_low, name="低一", char_count=51, spoken="字" * 51)
    over = replace(edge_high, name="高一", char_count=97, spoken="字" * 97, hook_id="h6")
    bounded = evaluate((edge_low, edge_high, under, over), gates)
    failed = {item.name for item in bounded.length_failures}
    assert failed == {"低一", "高一"}


def test_hook_collision_and_reuse():
    gates = Gates(
        min_chars=1,
        max_chars=500,
        simhash_hamming_max=0,
        jaccard_max=1.0,
        pair_rule="both",
        hook_hamming_max=16,
        hook_jaccard_max=0.45,
        max_hook_reuse=2,
    )
    near_a = _script("甲", "h01", "天一冷，膝盖就跟针扎一样？", "三层锁温，前后左右都包住。")
    near_b = _script("乙", "h02", "天一冷膝盖就跟针扎一样？", "关节处留了活动褶，下蹲不勒。")
    other = _script("丙", "h03", "儿女不在身边，膝盖疼了自己忍？", "夜里睡觉垫着也不容易掉。")
    report = evaluate((near_a, near_b, other), gates)
    assert [(item.left_id, item.right_id) for item in report.hook_collisions] == [
        ("h01", "h02")
    ]
    reused = (
        _script("一", "h01", "同一句钩子啊", "卖点甲写清楚。"),
        _script("二", "h01", "同一句钩子啊", "卖点乙写清楚。"),
        _script("三", "h01", "同一句钩子啊", "卖点丙写清楚。"),
    )
    reuse_report = evaluate(reused, gates)
    assert reuse_report.hook_collisions == ()
    assert reuse_report.hook_reuse[0].count == 3
    assert reuse_report.hook_reuse[0].over
    assert not reuse_report.passed


def test_similar_pair_requires_both_metrics():
    atoms = load_atoms(ATOMS)
    scripts = expand(atoms).scripts
    left = next(
        script
        for script in scripts
        if script.selling_point_label == "卖点05"
        and script.hook_id == "h01"
        and script.scene_label == "办公室"
    )
    right = next(
        script
        for script in scripts
        if script.selling_point_label == "卖点09"
        and script.hook_id == "h01"
        and script.scene_label == "办公室"
    )
    base = Gates(
        min_chars=1,
        max_chars=500,
        simhash_hamming_max=12,
        jaccard_max=0.99,
        hook_hamming_max=0,
        hook_jaccard_max=1.0,
        max_hook_reuse=10,
    )
    both = evaluate((left, right), replace(base, pair_rule="both"))
    either = evaluate((left, right), replace(base, pair_rule="either"))
    assert both.similar_pairs == ()
    assert len(either.similar_pairs) == 1
    assert both.passed
    assert not either.passed


def test_example_fails_three_gates_and_keeps_a_diverse_pair():
    atoms = load_atoms(ATOMS)
    expanded = expand(atoms)
    report = evaluate(expanded.scripts, atoms.gates)
    assert not report.passed
    reasons = {item.reason for item in report.length_failures}
    assert reasons == {"short", "long"}
    assert len(report.length_failures) == 24
    assert [(item.left_id, item.right_id) for item in report.hook_collisions] == [
        ("h01", "h02")
    ]
    assert not any(item.over for item in report.hook_reuse)
    assert 0 < len(report.similar_pairs) < report.pair_count
    flagged = {(item.left, item.right) for item in report.similar_pairs}
    by_key = {
        (script.selling_point_label, script.hook_id, script.scene_label): script
        for script in expanded.scripts
    }
    near_left = by_key[("卖点05", "h01", "办公室")]
    near_right = by_key[("卖点06", "h01", "办公室")]
    diverse = by_key[("卖点09", "h01", "办公室")]
    assert (near_left.name, near_right.name) in flagged or (
        near_right.name,
        near_left.name,
    ) in flagged
    assert (near_left.name, diverse.name) not in flagged
    assert (diverse.name, near_left.name) not in flagged
    short = by_key[("卖点08", "h01", "办公室")]
    long = by_key[("卖点07", "h01", "办公室")]
    failed = {item.name for item in report.length_failures}
    assert short.name in failed
    assert long.name in failed
    assert near_left.name not in failed
    assert diverse.name not in failed
