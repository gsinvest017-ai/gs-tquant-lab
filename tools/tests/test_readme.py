"""Parity tests for tools/README.md against the actual tools/ tree.

Stdlib-only unittest. tools/README.md is the toolchain reference doc (M20);
its "## Tools" table lists every shipped tool. Nothing stops that table from
silently rotting when a tool is added / removed / renamed -- exactly the
"true only by convention" gap that M9 (orphan detection), M18 (check_all == CI
workflow) and M19 (.gitattributes == _HANDWRITTEN_DIR_PARTS) each closed by
locking the invariant into a test. These tests are the same move for the
README: the documented tool set must equal the real tool set.

The yaml/gitattributes guards parse a sibling config file; here we parse the
README's Tools table with a deliberately narrow regex and assert its shape
first (test_tools_table_shape) so a reformat fails loudly rather than being
mis-read as an empty table.

Run:
    python3 tools/tests/test_readme.py
    # or
    python3 -m unittest tools.tests.test_readme
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
README = TOOLS / 'README.md'

# A table data row whose first cell is a backticked `tools/...` path.
_TOOL_ROW_RE = re.compile(r'^\|\s*`(tools/[^`]+)`\s*\|')
# The 4 shipped Python tools live at tools/<name>.py (no deeper nesting).
_TOPLEVEL_PY_RE = re.compile(r'^tools/[^/]+\.py$')
# Hook scripts that must also be documented.
_HOOK_PATHS = {'tools/hooks/pre-commit', 'tools/hooks/install.sh'}


def _tools_section() -> list[str]:
    """Lines of the README's `## Tools` section (up to the next `## ` header)."""
    lines = README.read_text(encoding='utf-8').splitlines()
    out: list[str] = []
    in_section = False
    for ln in lines:
        if ln.startswith('## '):
            if in_section:
                break
            in_section = ln.strip() == '## Tools'
            continue
        if in_section:
            out.append(ln)
    return out


def _documented_tool_paths() -> set[str]:
    """Backticked `tools/...` paths in the first column of the Tools table."""
    paths: set[str] = set()
    for ln in _tools_section():
        m = _TOOL_ROW_RE.match(ln)
        if m:
            paths.add(m.group(1))
    return paths


def _actual_toplevel_py() -> set[str]:
    return {f'tools/{p.name}' for p in TOOLS.glob('*.py')}


class ReadmeParityTests(unittest.TestCase):
    def test_readme_exists(self):
        self.assertTrue(README.is_file(), f'missing toolchain reference: {README}')

    def test_tools_table_shape(self):
        # Guards the narrow parser: the Tools section must contain a markdown
        # table (header separator row) and at least one `tools/...` data row.
        # If someone reformats the table away from this shape, fail loudly so
        # the parser gets updated rather than silently reading zero tools.
        section = _tools_section()
        self.assertTrue(section, 'no "## Tools" section in README')
        self.assertTrue(
            any(re.match(r'^\|[\s:|-]+\|', ln) for ln in section),
            'Tools section has no markdown table separator row',
        )
        self.assertTrue(
            _documented_tool_paths(),
            'Tools table has no `tools/...` rows; update _TOOL_ROW_RE',
        )

    def test_all_toplevel_py_tools_documented(self):
        documented_py = {p for p in _documented_tool_paths() if _TOPLEVEL_PY_RE.match(p)}
        actual = _actual_toplevel_py()
        self.assertEqual(
            documented_py, actual,
            'tools/README.md Tools table drifted from the real tools/*.py set.\n'
            f'  documented: {sorted(documented_py)}\n'
            f'  on disk:    {sorted(actual)}\n'
            'Update the "## Tools" table in tools/README.md and the tools/ tree '
            'together.',
        )

    def test_hook_scripts_documented(self):
        documented = _documented_tool_paths()
        for hook in sorted(_HOOK_PATHS):
            self.assertIn(
                hook, documented,
                f'{hook} exists but is not in the README Tools table',
            )

    def test_no_undocumented_or_phantom_paths(self):
        # Every backticked path in the table must point at a real file (catches
        # typos / a tool documented but never committed, and the reverse via
        # test_all_toplevel_py_tools_documented).
        for path in sorted(_documented_tool_paths()):
            self.assertTrue(
                (REPO / path).exists(),
                f'README Tools table lists `{path}` but it does not exist',
            )

    def test_hook_scripts_exist_on_disk(self):
        # Positive anchor: the documented hook paths are real (parity is only
        # meaningful if both sides describe existing files).
        for hook in sorted(_HOOK_PATHS):
            self.assertTrue((REPO / hook).is_file(), f'missing hook script: {hook}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
