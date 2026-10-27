"""Write ``scripts.csv`` and ``report.md``."""

from __future__ import annotations

import csv
from pathlib import Path

from touliu_script_matrix import __version__
from touliu_script_matrix.atoms import Atoms
from touliu_script_matrix.expand import ExpandResult, Script
from touliu_script_matrix.gates import GateReport

CSV_FIELDS = [
    "name",
    "index",
    "hook_id",
    "hook",
    "selling_point_id",
    "selling_point_label",
    "selling_point",
    "audience",
    "tone",
    "scene_label",
    "scene",
    "cta",
    "part_hook",
    "part_body",
    "part_cta",
    "script",
    "spoken",
    "char_count",
    "length_ok",
]

_LENGTH_WORD = {"short": "过短 / short", "long": "过长 / long"}


def write_outputs(
    atoms: Atoms,
    expanded: ExpandResult,
    report: GateReport,
    out_dir: str | Path,
    *,
    with_report: bool,
) -> tuple[Path, Path | None]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    csv_path = target / "scripts.csv"
    _write_csv(expanded.scripts, report, csv_path)
    if not with_report:
        return csv_path, None
    report_path = target / "report.md"
    report_path.write_text(
        render_report(atoms, expanded, report),
        encoding="utf-8",
    )
    return csv_path, report_path


def _write_csv(
    scripts: tuple[Script, ...], report: GateReport, path: Path
) -> None:
    failed = {item.name for item in report.length_failures}
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for script in scripts:
            writer.writerow(
                {
                    "name": script.name,
                    "index": script.index,
                    "hook_id": script.hook_id,
                    "hook": script.hook,
                    "selling_point_id": script.selling_point_id,
                    "selling_point_label": script.selling_point_label,
                    "selling_point": script.selling_point,
                    "audience": script.audience,
                    "tone": script.tone,
                    "scene_label": script.scene_label,
                    "scene": script.scene,
                    "cta": script.cta,
                    "part_hook": script.part_hook,
                    "part_body": script.part_body,
                    "part_cta": script.part_cta,
                    "script": script.script,
                    "spoken": script.spoken,
                    "char_count": script.char_count,
                    "length_ok": "false" if script.name in failed else "true",
                }
            )


def render_report(atoms: Atoms, expanded: ExpandResult, report: GateReport) -> str:
    gates = atoms.gates
    verdict = "PASS" if report.passed else "FAIL"
    counts = [script.char_count for script in expanded.scripts]
    if counts:
        length_line = (
            f"- 字数范围 / chars: min {min(counts)}, "
            f"median {_median(counts)}, max {max(counts)}"
        )
    else:
        length_line = "- 字数范围 / chars: （空矩阵 / empty）"
    listed = report.similar_pairs[: gates.pair_list_limit]
    reuse_over = sum(1 for item in report.hook_reuse if item.over)
    lines = [
        "# 口播脚本矩阵门禁报告",
        "",
        "Script Matrix Gate Report",
        "",
        f"- 工具 / tool: touliu-script-matrix {__version__}",
        f"- 产品 / product: {atoms.product}",
        f"- 原子 / atoms: `{atoms.source}`",
        (
            f"- 展开 / expanded: {report.script_count} / {expanded.total_combos}"
            + (f" (limit {expanded.limit})" if expanded.limit is not None else "")
        ),
        f"- 结果 / result: **{verdict}**",
        "",
        "## 阈值 / Thresholds",
        "",
        "| Gate | Value |",
        "| --- | --- |",
        f"| 字数 / chars | {gates.min_chars}–{gates.max_chars} |",
        f"| shingle n | {gates.shingle_n} |",
        f"| SimHash Hamming ≤ | {gates.simhash_hamming_max} |",
        f"| Jaccard ≥ | {gates.jaccard_max:.2f} |",
        f"| 脚本对规则 / pair rule | {gates.pair_rule} |",
        f"| 钩子 Hamming ≤ | {gates.hook_hamming_max} |",
        f"| 钩子 Jaccard ≥ | {gates.hook_jaccard_max:.2f} |",
        f"| 钩子复用上限 / max hook reuse | {gates.max_hook_reuse} |",
        "",
        "脚本对在 `both` 下要同时越过 SimHash 和 Jaccard 才算近复制；`either` 是两者任一越过。钩子碰撞看钩子文本本身，任一指标越过即碰撞。",
        "",
        "A script pair fails under `both` only when SimHash and Jaccard both call it a near copy. Hook text collides when either hook metric is over its line.",
        "",
        "## 字数门禁 / Length",
        "",
        length_line,
        f"- 通过 / pass: {report.script_count - len(report.length_failures)}",
        f"- 失败 / fail: {len(report.length_failures)}",
        "",
        "| name | chars | reason |",
        "| --- | ---: | --- |",
    ]
    if report.length_failures:
        for item in report.length_failures:
            lines.append(
                f"| {_md(item.name)} | {item.char_count} | {_LENGTH_WORD[item.reason]} |"
            )
    else:
        lines.append("| — | — | — |")
    lines.extend(
        [
            "",
            "## 钩子碰撞 / Hook collisions",
            "",
            f"- 碰撞对数 / colliding pairs: {len(report.hook_collisions)}",
            "",
            "| left | right | hamming | jaccard |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    if report.hook_collisions:
        for item in report.hook_collisions:
            lines.append(
                "| {left} `{lid}` | {right} `{rid}` | {ham} | {jac:.3f} |".format(
                    left=_md(item.left_text),
                    lid=item.left_id,
                    right=_md(item.right_text),
                    rid=item.right_id,
                    ham=item.hamming,
                    jac=item.jaccard,
                )
            )
    else:
        lines.append("| — | — | — | — |")
    lines.extend(
        [
            "",
            "## 钩子复用 / Hook reuse",
            "",
            f"- 超过上限 / over cap: {reuse_over}",
            "",
            "| hook_id | count | max | status |",
            "| --- | ---: | ---: | --- |",
        ]
    )
    if report.hook_reuse:
        for item in report.hook_reuse:
            status = "FAIL" if item.over else "ok"
            lines.append(
                f"| {_md(item.hook_id)} | {item.count} | {item.limit} | {status} |"
            )
    else:
        lines.append("| — | — | — | — |")
    lines.extend(
        [
            "",
            "## 相似脚本对 / Similar pairs",
            "",
            f"- 配对数 / pairs compared: {report.pair_count}",
            f"- 命中 / flagged: {len(report.similar_pairs)}",
            f"- 下列出 / listed: {len(listed)}",
            "",
            "| left | right | hamming | jaccard |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    if listed:
        for item in listed:
            lines.append(
                f"| {_md(item.left)} | {_md(item.right)} | {item.hamming} | {item.jaccard:.3f} |"
            )
    else:
        lines.append("| — | — | — | — |")
    reason = _verdict_sentence(report, reuse_over)
    lines.extend(
        [
            "",
            "## 结论 / Verdict",
            "",
            f"**{verdict}**. {reason}",
            "",
            "前 3 秒是钩子，中 10 秒是卖点，尾 2 秒是 CTA。字数按口播正文计（不含栏目标签，不计空白），用来近似 15 秒篇幅，不是语音合成测时。",
            "",
            "The three lines are the 3s hook, the 10s selling point, and the 2s CTA. 字数 counts the spoken line without labels or whitespace. It is a length budget for about 15 seconds, not a timed voice render.",
            "",
            "本地生成，无登录、无发布、无云端 API。",
            "",
            "Generated locally. No login, no posting, no cloud API.",
            "",
        ]
    )
    return "\n".join(lines)


def _median(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[(len(ordered) - 1) // 2]


def _md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def _verdict_sentence(report: GateReport, reuse_over: int) -> str:
    if report.passed:
        return "字数、钩子和脚本对都在阈值内。Length, hooks, and script pairs are inside the gates."
    return (
        f"字数越界 {len(report.length_failures)} 条，"
        f"钩子碰撞 {len(report.hook_collisions)} 对，"
        f"钩子复用超限 {reuse_over} 条，"
        f"相似脚本 {len(report.similar_pairs)} 对。"
        "Length, hook, reuse, or near-copy gate failed."
    )
