"""Convert every .ipynb in the repo to a sibling .py file.

Pure stdlib — no nbformat/nbconvert dependency. Strips outputs.
Markdown / raw cells become comment blocks; code cells are emitted verbatim.
Magics (lines starting with % or !) are commented out so the .py is importable.

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
import sys
from pathlib import Path


HEADER = '# -*- coding: utf-8 -*-\n# Auto-generated from {src} by tools/ipynb_to_py.py\n# Do not edit by hand; re-run the converter to regenerate.\n\n'
CELL_SEP = '# %% [{kind}] cell {idx}\n'


def _comment_block(text: str) -> str:
    lines = text.splitlines() or ['']
    return '\n'.join('# ' + ln if ln else '#' for ln in lines) + '\n'


def _sanitize_code(text: str) -> str:
    out = []
    for ln in text.splitlines():
        stripped = ln.lstrip()
        if stripped.startswith(('%', '!', '?')) or stripped.endswith('?'):
            out.append('# ' + ln)
        else:
            out.append(ln)
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
