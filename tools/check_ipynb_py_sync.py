"""Verify every .ipynb has an up-to-date .py sibling.

For each notebook, regenerate the expected .py text in memory via
``ipynb_to_py.convert_to_str`` and diff against the .py on disk.
Reports drift (out-of-sync) and missing siblings.

Exit codes:
  0 — all pairs in sync
  1 — usage error / nothing to check
  2 — drift or missing sibling detected

Designed to run in CI as the back-stop to the opt-in pre-commit hook.
"""
from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ipynb_to_py import convert_to_str  # noqa: E402


def _pairs(root: Path) -> list[tuple[Path, Path]]:
    out = []
    for nb in root.rglob('*.ipynb'):
        if '.ipynb_checkpoints' in nb.parts:
            continue
        out.append((nb, nb.with_suffix('.py')))
    return sorted(out)


def _diff_preview(expected: str, actual: str, rel: Path, max_lines: int = 20) -> str:
    diff = difflib.unified_diff(
        actual.splitlines(keepends=True),
        expected.splitlines(keepends=True),
        fromfile=f'{rel} (on disk)',
        tofile=f'{rel} (expected from .ipynb)',
        n=2,
    )
    lines = list(diff)
    if len(lines) > max_lines:
        lines = lines[:max_lines] + [f'... ({len(lines) - max_lines} more diff lines truncated)\n']
    return ''.join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default='.', help='Repo root to scan')
    parser.add_argument('--quiet', action='store_true', help='Only print summary')
    parser.add_argument('--no-diff', action='store_true', help='Do not print unified diff for drifted files')
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    pairs = _pairs(root)
    if not pairs:
        print(f'No .ipynb files under {root}', file=sys.stderr)
        return 1

    missing: list[Path] = []
    drift: list[tuple[Path, str, str]] = []  # (relpath, expected, actual)
    errors: list[tuple[Path, str]] = []

    for nb, py in pairs:
        try:
            rel = nb.relative_to(root)
        except ValueError:
            rel = nb
        if not py.exists():
            missing.append(rel)
            continue
        try:
            expected = convert_to_str(nb)
        except Exception as e:  # noqa: BLE001
            errors.append((rel, f'{type(e).__name__}: {e}'))
            continue
        actual = py.read_text(encoding='utf-8', errors='replace')
        if expected != actual:
            drift.append((rel, expected, actual))

    total = len(pairs)
    bad = len(missing) + len(drift) + len(errors)
    ok = total - bad

    print(f'Checked {total} ipynb/py pairs under {root}')
    print(f'  In sync:                  {ok}')
    print(f'  Missing .py sibling:      {len(missing)}')
    print(f'  Out-of-sync (drifted):    {len(drift)}')
    print(f'  Conversion errors:        {len(errors)}')

    if not args.quiet:
        for rel in missing:
            print(f'  MISSING: {rel} (no .py — run: python3 tools/ipynb_to_py.py {rel})')
        for rel, msg in errors:
            print(f'  ERROR:   {rel}: {msg}')
        for rel, expected, actual in drift:
            print(f'  DRIFT:   {rel}')
            if not args.no_diff:
                print(_diff_preview(expected, actual, rel))

    if bad:
        print('\nFIX: re-run  python3 tools/ipynb_to_py.py .  and commit the updated .py files.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
