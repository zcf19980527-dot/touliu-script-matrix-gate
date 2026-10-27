"""Command line: expand, check, and demo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from touliu_script_matrix import __version__
from touliu_script_matrix.atoms import AtomsError, load_atoms
from touliu_script_matrix.expand import expand
from touliu_script_matrix.gates import evaluate
from touliu_script_matrix.report import write_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="touliu_script_matrix",
        description=(
            "Expand oral-script atoms into a 15s matrix and gate "
            "length, hook collisions, and near-duplicate copy. Local only."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"touliu-script-matrix {__version__}",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    expand_parser = sub.add_parser(
        "expand",
        help="write the script matrix CSV",
    )
    _add_io(expand_parser)
    expand_parser.set_defaults(func=_cmd_expand)

    check_parser = sub.add_parser(
        "check",
        help="write the CSV and the gate report; exit 1 when the gate fails",
    )
    _add_io(check_parser)
    check_parser.set_defaults(func=_cmd_check)

    demo_parser = sub.add_parser(
        "demo",
        help="expand and check the sample atoms; exit 0 after writing the report",
    )
    _add_io(demo_parser)
    demo_parser.set_defaults(func=_cmd_demo)
    return parser


def _add_io(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--atoms",
        default="examples/atoms.yaml",
        help="atom file (default: examples/atoms.yaml, from the repo root)",
    )
    parser.add_argument(
        "--out",
        default="examples/out",
        help="output directory (default: examples/out)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="override the atom file limit",
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except AtomsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def console_main() -> None:
    raise SystemExit(main())


def _cmd_expand(args: argparse.Namespace) -> int:
    return _run(args, with_report=False, fail_on_gate=False)


def _cmd_check(args: argparse.Namespace) -> int:
    return _run(args, with_report=True, fail_on_gate=True)


def _cmd_demo(args: argparse.Namespace) -> int:
    return _run(args, with_report=True, fail_on_gate=False)


def _run(args: argparse.Namespace, *, with_report: bool, fail_on_gate: bool) -> int:
    if args.limit is not None and args.limit < 1:
        print("error: --limit must be a positive integer", file=sys.stderr)
        return 2
    atoms_path = Path(args.atoms)
    atoms = load_atoms(atoms_path)
    expanded = expand(atoms, limit=args.limit)
    report = evaluate(expanded.scripts, atoms.gates)
    csv_path, report_path = write_outputs(
        atoms,
        expanded,
        report,
        args.out,
        with_report=with_report,
    )
    verdict = "PASS" if report.passed else "FAIL"
    print(f"product: {atoms.product}")
    print(
        f"scripts: {report.script_count} / {expanded.total_combos}"
        + (f" (limit {expanded.limit})" if expanded.limit is not None else "")
    )
    print(f"gate: {verdict}")
    print(f"length failures: {len(report.length_failures)}")
    print(f"hook collisions: {len(report.hook_collisions)}")
    print(f"hook reuse over cap: {sum(1 for item in report.hook_reuse if item.over)}")
    print(f"similar pairs: {len(report.similar_pairs)}")
    print(f"wrote {csv_path}")
    if report_path is not None:
        print(f"wrote {report_path}")
    if fail_on_gate and not report.passed:
        return 1
    return 0
