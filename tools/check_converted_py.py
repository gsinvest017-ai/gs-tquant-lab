"""Validate every .py sibling of an .ipynb in the repo.

Two checks, stdlib-only:

1. ``py_compile`` — proves the file is syntactically valid Python (so any
   uncommented IPython magic or stray markdown would be caught immediately).
2. Magic sniff — scans for lines starting with ``!``, ``%`` or ``?`` that
   the converter should have commented out.

Exit code 0 iff every paired .py passes both checks. Designed to be run
in CI after ``tools/ipynb_to_py.py``.
"""
from __future__ import annotations

import argparse
import os
import py_compile
import re
import sys
import tempfile
from pathlib import Path


MAGIC_RE = re.compile(r'^(!|%|\?)')


def _paired_py_files(root: Path) -> list[tuple[Path, Path]]:
    pairs = []
    for nb in root.rglob('*.ipynb'):
        if '.ipynb_checkpoints' in nb.parts:
            continue
        py = nb.with_suffix('.py')
        pairs.append((nb, py))
    return pairs


def _compile_check(py: Path) -> str | None:
    with tempfile.NamedTemporaryFile(suffix='.pyc', delete=False) as tmp:
        cfile = tmp.name
    try:
        py_compile.compile(str(py), cfile=cfile, doraise=True)
        return None
    except py_compile.PyCompileError as e:
        msg = str(e).strip().splitlines()
        return msg[-1] if msg else 'PyCompileError'
    except Exception as e:  # pragma: no cover - defensive
        return f'{type(e).__name__}: {e}'
    finally:
        try:
            os.unlink(cfile)
        except OSError:
            pass


def _magic_check(py: Path) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []
    text = py.read_text(encoding='utf-8', errors='replace')
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if MAGIC_RE.match(stripped):
            hits.append((i, line[:120]))
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', nargs='?', default='.', help='Repo root to scan')
    parser.add_argument('--quiet', action='store_true', help='Only print summary')
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    pairs = _paired_py_files(root)
    if not pairs:
        print(f'No .ipynb files under {root}', file=sys.stderr)
        return 1

    missing: list[Path] = []
    compile_fail: list[tuple[Path, str]] = []
    magic_fail: list[tuple[Path, list[tuple[int, str]]]] = []

    for nb, py in pairs:
        if not py.exists():
            missing.append(nb)
            continue
        err = _compile_check(py)
        if err is not None:
            compile_fail.append((py, err))
        magics = _magic_check(py)
        if magics:
            magic_fail.append((py, magics))

    total = len(pairs)
    bad = len(missing) + len(compile_fail) + len(magic_fail)
    ok = total - bad

    print(f'Checked {total} ipynb/py pairs under {root}')
    print(f'  OK:                  {ok}')
    print(f'  Missing .py sibling: {len(missing)}')
    print(f'  py_compile failures: {len(compile_fail)}')
    print(f'  Magic-line leaks:    {len(magic_fail)}')

    if not args.quiet:
        for nb in missing:
            print(f'  MISSING: {nb}')
        for py, err in compile_fail:
            print(f'  COMPILE: {py}: {err}')
        for py, hits in magic_fail:
            print(f'  MAGIC: {py}')
            for lineno, content in hits[:5]:
                print(f'    line {lineno}: {content}')
            if len(hits) > 5:
                print(f'    ... and {len(hits) - 5} more')

    return 0 if bad == 0 else 2


if __name__ == '__main__':
    sys.exit(main())
