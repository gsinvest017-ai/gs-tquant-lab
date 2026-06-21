"""Validate every .py sibling of an .ipynb in the repo.

Two checks, stdlib-only:

1. ``py_compile`` — proves the file is syntactically valid Python (so any
   uncommented IPython magic or stray markdown would be caught immediately).
2. Magic sniff — scans for lines the converter should have commented out:
   line/cell/prefix magics (``!``/``%``/``?``) and suffix help (a bare
   reference chain ending in ``?``/``??``, e.g. ``df.head?``).

The magic sniff is string-aware: a line that BEGINS inside a triple-quoted
string is never a leaked magic, it is string content the converter
deliberately preserves verbatim (see ipynb_to_py._advance_string_state). It
reuses the converter's own string scanner so a docstring such as
``\"\"\"\\n!run this\\n%(name)s\\n\"\"\"`` is not falsely flagged — without
this, the converter (string-aware since the M31 fix) and this validator would
disagree, turning a correct conversion into a red CI build.

The "is this a magic line" predicate is *also* the converter's own
(``ipynb_to_py._is_magic_line``), imported rather than re-implemented. Before
M33 this validator carried a third independent copy (a bare ``^[!%?]`` regex)
that could not name a leaked suffix-help line — it only surfaced as a cryptic
``py_compile`` SyntaxError. Sharing one predicate closes that asymmetry and
guarantees the two tools never disagree on what counts as a magic.

Exit code 0 iff every paired .py passes both checks. Designed to be run
in CI after ``tools/ipynb_to_py.py``.
"""
from __future__ import annotations

import argparse
import os
import py_compile
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ipynb_to_py import _advance_string_state, _is_magic_line  # noqa: E402


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
    state = None  # triple-quoted-string state across physical lines
    for i, line in enumerate(text.splitlines(), 1):
        if state is None and _is_magic_line(line.lstrip()):
            hits.append((i, line[:120]))
        state = _advance_string_state(line, state)
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
