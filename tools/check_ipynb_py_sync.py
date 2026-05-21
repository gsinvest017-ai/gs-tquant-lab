"""Verify every .ipynb has an up-to-date .py sibling.

For each notebook, regenerate the expected .py text in memory via
``ipynb_to_py.convert_to_str`` and diff against the .py on disk.
Reports drift (out-of-sync), missing siblings, and orphan .py files
(a .py with no matching .ipynb, e.g. left behind after a notebook was
renamed or deleted).

Exit codes:
  0 — all pairs in sync, no orphans
  1 — usage error / nothing to check
  2 — drift, missing sibling, or orphan .py detected

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


# Directories whose .py files are hand-written, not generated from notebooks.
# Anything under these prefixes is exempt from orphan-detection.
_HANDWRITTEN_DIR_PARTS = ('tools',)
# Directories that should be skipped entirely during the walk.
_SKIP_DIR_PARTS = ('.git', '.github', '.ipynb_checkpoints', '__pycache__', '.venv', 'venv')


def _pairs(root: Path) -> list[tuple[Path, Path]]:
    out = []
    for nb in root.rglob('*.ipynb'):
        if '.ipynb_checkpoints' in nb.parts:
            continue
        out.append((nb, nb.with_suffix('.py')))
    return sorted(out)


def _orphan_py(root: Path) -> list[Path]:
    """Return .py files under root that have no matching .ipynb sibling.

    Excludes hand-written tooling (``tools/``) and standard non-source dirs.
    Returned paths are sorted, relative-to-root when possible.
    """
    out: list[Path] = []
    for py in root.rglob('*.py'):
        parts = py.parts
        if any(part in _SKIP_DIR_PARTS for part in parts):
            continue
        if any(part in _HANDWRITTEN_DIR_PARTS for part in parts):
            continue
        if py.with_suffix('.ipynb').exists():
            continue
        try:
            out.append(py.relative_to(root))
        except ValueError:
            out.append(py)
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

    orphans = _orphan_py(root)

    total = len(pairs)
    bad = len(missing) + len(drift) + len(errors) + len(orphans)
    ok = total - len(missing) - len(drift) - len(errors)

    print(f'Checked {total} ipynb/py pairs under {root}')
    print(f'  In sync:                  {ok}')
    print(f'  Missing .py sibling:      {len(missing)}')
    print(f'  Out-of-sync (drifted):    {len(drift)}')
    print(f'  Conversion errors:        {len(errors)}')
    print(f'  Orphan .py (no .ipynb):   {len(orphans)}')

    if not args.quiet:
        for rel in missing:
            print(f'  MISSING: {rel} (no .py — run: python3 tools/ipynb_to_py.py {rel})')
        for rel, msg in errors:
            print(f'  ERROR:   {rel}: {msg}')
        for rel, expected, actual in drift:
            print(f'  DRIFT:   {rel}')
            if not args.no_diff:
                print(_diff_preview(expected, actual, rel))
        for rel in orphans:
            print(f'  ORPHAN:  {rel} (no matching .ipynb — delete it or restore the notebook)')

    if bad:
        print('\nFIX: re-run  python3 tools/ipynb_to_py.py .  and commit the updated .py files.', file=sys.stderr)
        if orphans:
            print('     For orphans, delete the stale .py or restore the missing .ipynb.', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
