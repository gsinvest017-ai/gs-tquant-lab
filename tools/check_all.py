#!/usr/bin/env python3
"""Run the full .ipynb -> .py toolchain validation suite in one command.

Single local entry point that mirrors `.github/workflows/ipynb-py-sync.yml`
step-for-step, so `python3 tools/check_all.py` reproduces exactly what CI
gates on. Keeping local == CI means a green local run predicts a green CI run
(and a red one tells you what to fix before pushing):

  1. unit tests       python3 -m unittest discover -s tools/tests
  2. strict pre-scan  python3 tools/ipynb_to_py.py --strict --dry-run <root>
  3. sync check       python3 tools/check_ipynb_py_sync.py <root>
  4. converted check  python3 tools/check_converted_py.py <root>

All steps run (no fail-fast) so a single invocation surfaces every problem at
once -- same try-all rationale as ipynb_to_py.py --strict. Exit 0 iff every
step passes; exit 1 if any step fails.

Usage:
    python3 tools/check_all.py              # full suite against the repo root
    python3 tools/check_all.py --quiet      # checkers print summaries only
    python3 tools/check_all.py --skip-tests # skip the unittest step (fast wiring check)
    python3 tools/check_all.py <root>       # validate a different tree
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TOOLS_DIR.parent


def build_steps(root: str, *, quiet: bool = False, skip_tests: bool = False) -> list[tuple[str, list[str]]]:
    """Build the ordered (label, argv) list mirroring the CI workflow.

    `root` is passed verbatim to the converter / checkers as their positional
    path argument; the unittest step always discovers tools/tests under the
    real repo (it is repo-global, not root-scoped). argv[0] is always the
    current interpreter so the suite uses the same Python that launched it.
    """
    py = sys.executable
    quiet_flag = ['--quiet'] if quiet else []
    steps: list[tuple[str, list[str]]] = []
    if not skip_tests:
        steps.append((
            'unit tests',
            [py, '-m', 'unittest', 'discover', '-s', str(TOOLS_DIR / 'tests')],
        ))
    steps.append((
        'strict pre-scan (parse, no write)',
        [py, str(TOOLS_DIR / 'ipynb_to_py.py'), '--strict', '--dry-run', root],
    ))
    steps.append((
        'sync check (.py regenerable + in sync)',
        [py, str(TOOLS_DIR / 'check_ipynb_py_sync.py'), root] + quiet_flag,
    ))
    steps.append((
        'converted check (compile + no magic leaks)',
        [py, str(TOOLS_DIR / 'check_converted_py.py'), root] + quiet_flag,
    ))
    return steps


def _default_run(argv: list[str]) -> int:
    """Run one step as a subprocess, streaming its output, return its rc."""
    return subprocess.run(argv).returncode


def run_steps(steps, run=_default_run) -> list[tuple[str, int]]:
    """Run every step (no fail-fast). Return list of (label, returncode)."""
    results: list[tuple[str, int]] = []
    for label, argv in steps:
        rc = run(argv)
        results.append((label, rc))
    return results


def main(argv: list[str] | None = None, run=_default_run) -> int:
    ap = argparse.ArgumentParser(
        description='Run the full .ipynb->.py validation suite (mirrors CI).',
    )
    ap.add_argument('root', nargs='?', default=str(REPO_ROOT),
                    help='Tree to validate (default: repo root)')
    ap.add_argument('--quiet', action='store_true',
                    help='Pass --quiet to the sync / converted checkers')
    ap.add_argument('--skip-tests', action='store_true',
                    help='Skip the unittest discover step')
    args = ap.parse_args(argv)

    steps = build_steps(args.root, quiet=args.quiet, skip_tests=args.skip_tests)
    total = len(steps)
    results: list[tuple[str, int]] = []
    for idx, (label, step_argv) in enumerate(steps, start=1):
        print(f'==> [{idx}/{total}] {label}', flush=True)
        rc = run(step_argv)
        results.append((label, rc))
        print(f'    {"PASS" if rc == 0 else f"FAIL (rc={rc})"}', flush=True)

    failed = [label for label, rc in results if rc != 0]
    print('\n--- check_all summary ---')
    for label, rc in results:
        print(f'  {"ok  " if rc == 0 else "FAIL"}  {label}')
    if failed:
        print(f'\n{len(failed)}/{total} step(s) FAILED: {", ".join(failed)}')
        return 1
    print(f'\nAll {total} step(s) passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
