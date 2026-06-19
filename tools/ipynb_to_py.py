"""Convert every .ipynb in the repo to a sibling .py file.

Pure stdlib — no nbformat/nbconvert dependency. Strips outputs.
Markdown / raw cells become comment blocks; code cells are emitted verbatim.
Magics (lines starting with % or !) and IPython help syntax (a bare object
reference chain ending in `?`/`??`, e.g. `df.head?`, or the `?obj` prefix form)
are commented out so the .py is importable. The help-suffix match is anchored to
an identifier/attribute/subscript/call chain (see _HELP_SUFFIX_RE) rather than a
naive `endswith('?')`, so a legitimate line such as `x = run()  # done?` is left
untouched instead of being silently turned into a comment. Magic detection is
also string-aware (see _advance_string_state): a line that BEGINS inside a
triple-quoted string is never treated as a magic, so embedding a shell snippet
or `%`-template inside a docstring no longer corrupts the string body.

By default a malformed notebook is reported to stderr but the batch continues
and rc=0 if at least the loop completed; pass --strict to flip that into a
hard failure (rc=1) so CI catches corrupted notebooks instead of silently
swallowing them.

--dry-run never writes a .py, but it still *parses* every notebook so it can
double as a fast, side-effect-free validation pass: `--strict --dry-run` is the
cheapest way for CI to fail on a corrupted .ipynb without regenerating the whole
tree of .py siblings.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


HEADER = '# -*- coding: utf-8 -*-\n# Auto-generated from {src} by tools/ipynb_to_py.py\n# Do not edit by hand; re-run the converter to regenerate.\n\n'
CELL_SEP = '# %% [{kind}] cell {idx}\n'

# IPython suffix-help syntax: a bare object reference chain (identifier, dotted
# attributes, subscripts, calls) terminated by `?` or `??`. Matching this rather
# than `endswith('?')` keeps real Python whose line happens to end in `?` — a
# trailing-question comment (`run()  # ok?`) or a spaced expression — out of the
# comment-out branch, so valid code is never silently dropped.
_HELP_SUFFIX_RE = re.compile(r'^[A-Za-z_][\w.]*(?:\[[^\]]*\]|\([^)]*\))*\?{1,2}$')


def _comment_block(text: str) -> str:
    lines = text.splitlines() or ['']
    return '\n'.join('# ' + ln if ln else '#' for ln in lines) + '\n'


def _advance_string_state(line: str, state: str | None) -> str | None:
    """Return the triple-quoted-string state in effect at the END of `line`.

    `state` is None when not inside a triple-quoted string, otherwise the open
    delimiter (``\"\"\"`` or ``'''``). Normal single/double-quoted strings and
    ``#`` comments on the line are consumed so a triple-quote (or ``#``) sitting
    inside them does not flip the state. This is a deliberately small scanner —
    just enough to tell whether the NEXT line begins inside a triple-quoted
    string, which is the only case where a leading %/!/? is string content
    rather than an IPython magic.
    """
    i, n = 0, len(line)
    while i < n:
        if state is not None:
            end = line.find(state, i)
            if end == -1:
                return state
            i, state = end + 3, None
            continue
        if line.startswith('"""', i) or line.startswith("'''", i):
            delim = line[i:i + 3]
            end = line.find(delim, i + 3)
            if end == -1:
                return delim  # opens a triple string that runs past this line
            i = end + 3
            continue
        ch = line[i]
        if ch == '#':
            return None  # comment runs to end of line
        if ch in ('"', "'"):
            j = i + 1
            while j < n:
                if line[j] == '\\':
                    j += 2
                    continue
                if line[j] == ch:
                    break
                j += 1
            i = j + 1
            continue
        i += 1
    return state


def _sanitize_code(text: str) -> str:
    out = []
    state = None  # triple-quoted-string state across physical lines
    for ln in text.splitlines():
        stripped = ln.lstrip()
        in_string = state is not None
        if not in_string and (stripped.startswith(('%', '!', '?')) or _HELP_SUFFIX_RE.match(stripped)):
            out.append('# ' + ln)
        else:
            out.append(ln)
        state = _advance_string_state(ln, state)
    return '\n'.join(out) + ('\n' if not text.endswith('\n') else '')


def convert_to_str(src: Path) -> str:
    """Return the .py text that would be written for src, without touching disk."""
    nb = json.loads(src.read_text(encoding='utf-8'))
    parts = [HEADER.format(src=src.name)]
    for i, cell in enumerate(nb.get('cells', [])):
        kind = cell.get('cell_type', 'unknown')
        source = cell.get('source', '')
        if isinstance(source, list):
            source = ''.join(source)
        if not source.strip():
            continue
        parts.append('\n' + CELL_SEP.format(kind=kind, idx=i))
        if kind == 'code':
            parts.append(_sanitize_code(source))
        else:
            parts.append(_comment_block(source))
    return ''.join(parts)


def convert(src: Path, dst: Path) -> None:
    dst.write_text(convert_to_str(src), encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('root', nargs='?', default='.', help='Repo root to scan (ignored if --files given)')
    ap.add_argument('--files', nargs='+', metavar='IPYNB', help='Convert only the listed notebooks instead of walking root')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument(
        '--strict',
        action='store_true',
        help='Return rc=1 if any notebook fails to convert (default: log and continue)',
    )
    args = ap.parse_args(argv)

    if args.files:
        notebooks = [Path(f).resolve() for f in args.files]
        bad = [p for p in notebooks if p.suffix != '.ipynb' or not p.exists()]
        if bad:
            for p in bad:
                print(f'ERR not an existing .ipynb: {p}', file=sys.stderr)
            return 1
        base = Path.cwd().resolve()
    else:
        base = Path(args.root).resolve()
        notebooks = sorted(p for p in base.rglob('*.ipynb') if '.ipynb_checkpoints' not in p.parts)
        if not notebooks:
            print(f'No .ipynb under {base}', file=sys.stderr)
            return 1

    converted = 0
    failures = 0
    for nb in notebooks:
        py = nb.with_suffix('.py')
        try:
            rel = nb.relative_to(base)
            rel_py = py.relative_to(base)
        except ValueError:
            rel = nb
            rel_py = py
        if args.dry_run:
            print(f'[dry] {rel} -> {rel_py}')
            # Parse (but don't write) so --dry-run can validate notebooks.
            try:
                convert_to_str(nb)
            except Exception as e:  # noqa: BLE001
                failures += 1
                print(f'ERR {rel}: {e}', file=sys.stderr)
            continue
        try:
            convert(nb, py)
            converted += 1
            print(f'OK  {rel}')
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f'ERR {rel}: {e}', file=sys.stderr)
    print(f'\nConverted {converted}/{len(notebooks)} notebooks.')
    if args.strict and failures:
        print(f'[strict] {failures} notebook(s) failed to convert.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
