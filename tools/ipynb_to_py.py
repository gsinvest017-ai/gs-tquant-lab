"""Convert every .ipynb in the repo to a sibling .py file.

Pure stdlib — no nbformat/nbconvert dependency. Strips outputs.
Markdown / raw cells become comment blocks; code cells are emitted verbatim.
Magics (lines starting with % or !) are commented out so the .py is importable.
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


def convert(src: Path, dst: Path) -> None:
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
    dst.write_text(''.join(parts), encoding='utf-8')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('root', nargs='?', default='.', help='Repo root to scan')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    root = Path(args.root).resolve()
    notebooks = sorted(p for p in root.rglob('*.ipynb') if '.ipynb_checkpoints' not in p.parts)
    if not notebooks:
        print(f'No .ipynb under {root}', file=sys.stderr)
        return 1

    converted = 0
    for nb in notebooks:
        py = nb.with_suffix('.py')
        rel = nb.relative_to(root)
        if args.dry_run:
            print(f'[dry] {rel} -> {py.relative_to(root)}')
            continue
        try:
            convert(nb, py)
            converted += 1
            print(f'OK  {rel}')
        except Exception as e:  # noqa: BLE001
            print(f'ERR {rel}: {e}', file=sys.stderr)
    print(f'\nConverted {converted}/{len(notebooks)} notebooks.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
