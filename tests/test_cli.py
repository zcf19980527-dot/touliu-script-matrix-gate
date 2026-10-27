"""CLI subcommands expand, check, and demo."""

from __future__ import annotations

import csv
import os
import subprocess
import sys

from tests.conftest import ATOMS, ROOT
from touliu_script_matrix.cli import main


def test_demo_writes_csv_and_report(tmp_path):
    out = tmp_path / "out"
    code = main(["demo", "--atoms", str(ATOMS), "--out", str(out)])
    assert code == 0
    csv_path = out / "scripts.csv"
    report_path = out / "report.md"
    assert csv_path.is_file()
    assert report_path.is_file()
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["name"] == "保暖护膝_卖点05_办公室_001"
    assert rows[0]["length_ok"] == "true"
    assert "前3s钩子：" in rows[0]["script"]
    assert "中10s卖点：" in rows[0]["script"]
    assert "尾2s CTA：" in rows[0]["script"]
    short = next(row for row in rows if row["selling_point_label"] == "卖点08")
    long = next(row for row in rows if row["selling_point_label"] == "卖点07")
    assert short["length_ok"] == "false"
    assert long["length_ok"] == "false"
    report = report_path.read_text(encoding="utf-8")
    assert "**FAIL**" in report
    assert "字数门禁" in report
    assert "钩子碰撞" in report
    assert "相似脚本对" in report
    assert "保暖护膝_卖点05_办公室_001" in report
    assert "touliu-script-matrix 0.1.0" in report


def test_check_exits_nonzero_on_example(tmp_path):
    code = main(["check", "--atoms", str(ATOMS), "--out", str(tmp_path)])
    assert code == 1
    assert (tmp_path / "report.md").is_file()


def test_expand_writes_csv_only(tmp_path):
    code = main(
        ["expand", "--atoms", str(ATOMS), "--out", str(tmp_path), "--limit", "2"]
    )
    assert code == 0
    with (tmp_path / "scripts.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["name"] for row in rows] == [
        "保暖护膝_卖点05_办公室_001",
        "保暖护膝_卖点05_办公室_002",
    ]
    assert not (tmp_path / "report.md").exists()


def test_check_exits_zero_when_clean(tmp_path):
    atoms = tmp_path / "atoms.yaml"
    atoms.write_text(
        """
product: 清爽品
limit: 2
gates:
  min_chars: 1
  max_chars: 500
  simhash_hamming_max: 0
  jaccard_max: 1.0
  pair_rule: both
  hook_hamming_max: 0
  hook_jaccard_max: 1.0
  max_hook_reuse: 5
hooks:
  - {id: h1, text: "早上出门膝盖发凉吗"}
  - {id: h2, text: "这双鞋垫跟护膝不是一回事"}
selling_points:
  - {id: "01", label: 卖点01, text: "薄绒一层，室内走动刚好。"}
audiences: ["中老年朋友"]
tones: ["说句实在的，"]
ctas: ["先看尺码。"]
scenes:
  - {id: office, label: 办公室, text: 办公室久坐}
""",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    code = main(["check", "--atoms", str(atoms), "--out", str(out)])
    assert code == 0
    report = (out / "report.md").read_text(encoding="utf-8")
    assert "**PASS**" in report


def test_usage_errors_exit_2(tmp_path, capsys):
    missing = main(["demo", "--atoms", str(tmp_path / "nope.yaml"), "--out", str(tmp_path)])
    assert missing == 2
    assert "not found" in capsys.readouterr().err
    bad_limit = main(["expand", "--atoms", str(ATOMS), "--limit", "0"])
    assert bad_limit == 2
    assert "--limit" in capsys.readouterr().err


def test_module_entrypoint_demo(tmp_path):
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "touliu_script_matrix",
            "demo",
            "--atoms",
            str(ATOMS),
            "--out",
            str(tmp_path),
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, proc.stderr
    assert "gate: FAIL" in proc.stdout
    assert (tmp_path / "scripts.csv").is_file()
    assert (tmp_path / "report.md").is_file()


def test_report_lists_thresholds_and_verdict(tmp_path):
    code = main(["demo", "--atoms", str(ATOMS), "--out", str(tmp_path)])
    assert code == 0
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert "60 / 480" in report
    assert "52–96" in report
    assert "both" in report
    assert "h01" in report
    assert "h02" in report
    assert "No login, no posting, no cloud API." in report
    assert "无登录、无发布、无云端 API。" in report
