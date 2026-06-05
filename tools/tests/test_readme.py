"""Parity tests for tools/README.md against the actual tools/ tree.

Stdlib-only unittest. tools/README.md is the toolchain reference doc (M20);
its "## Tools" table lists every shipped tool and its "## 測試" table lists
every test module. Nothing stops either table from silently rotting when a
tool / test module is added / removed / renamed -- exactly the "true only by
convention" gap that M9 (orphan detection), M18 (check_all == CI workflow) and
M19 (.gitattributes == _HANDWRITTEN_DIR_PARTS) each closed by locking the
invariant into a test. These tests are the same move for the README: the
documented tool set must equal the real tool set, and the documented test set
must equal the real test set.

  - ReadmeParityTests          -- "## Tools" table  vs  tools/*.py + hooks (M20)
  - ReadmeTestTableParityTests -- "## 測試" table   vs  tools/tests/test_*.py (M21)
  - ReadmeCiParityTests        -- "## CI 對應" list  vs  CI workflow run-steps (M22)

The yaml/gitattributes guards parse a sibling config file; here we parse the
README's tables with deliberately narrow regexes and assert each table's shape
first (test_*_table_shape) so a reformat fails loudly rather than being
mis-read as an empty table.

M22's ReadmeCiParityTests reuses M18's _step_signature / _workflow_run_commands
(from test_check_all) so the README CI list is normalized against the exact same
contract that already locks the workflow == build_steps. The HERE-on-sys.path
insert below makes that bare import work in every invocation mode (direct file,
`unittest discover`, and dotted `-m unittest tools.tests.test_readme`).

Run:
    python3 tools/tests/test_readme.py
    # or
    python3 -m unittest tools.tests.test_readme
"""
from __future__ import annotations

import re
import shlex
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
README = TOOLS / 'README.md'

# Reuse M18's normalization + workflow parser so the README CI guard shares the
# identical (tool, long_flags) contract that locks workflow == build_steps.
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from test_check_all import _step_signature, _workflow_run_commands  # noqa: E402

# A table data row whose first cell is a backticked `tools/...` path.
_TOOL_ROW_RE = re.compile(r'^\|\s*`(tools/[^`]+)`\s*\|')
# A table data row whose first cell is a backticked `tools/tests/...` path.
_TEST_ROW_RE = re.compile(r'^\|\s*`(tools/tests/[^`]+)`\s*\|')
# The 4 shipped Python tools live at tools/<name>.py (no deeper nesting).
_TOPLEVEL_PY_RE = re.compile(r'^tools/[^/]+\.py$')
# Hook scripts that must also be documented.
_HOOK_PATHS = {'tools/hooks/pre-commit', 'tools/hooks/pre-push', 'tools/hooks/install.sh'}


def _section(header: str) -> list[str]:
    """Lines under a `## <header>` section (up to the next `## ` header)."""
    lines = README.read_text(encoding='utf-8').splitlines()
    out: list[str] = []
    in_section = False
    for ln in lines:
        if ln.startswith('## '):
            if in_section:
                break
            in_section = ln.strip() == f'## {header}'
            continue
        if in_section:
            out.append(ln)
    return out


def _tools_section() -> list[str]:
    """Lines of the README's `## Tools` section."""
    return _section('Tools')


def _tests_section() -> list[str]:
    """Lines of the README's `## 測試` section."""
    return _section('測試')


def _documented_tool_paths() -> set[str]:
    """Backticked `tools/...` paths in the first column of the Tools table."""
    paths: set[str] = set()
    for ln in _tools_section():
        m = _TOOL_ROW_RE.match(ln)
        if m:
            paths.add(m.group(1))
    return paths


def _documented_test_paths() -> set[str]:
    """Backticked `tools/tests/...` paths in the first column of the 測試 table.

    Anchored to `^|` so the `python3 tools/tests/...` lines in the section's
    fenced code block are not mistaken for table rows.
    """
    paths: set[str] = set()
    for ln in _tests_section():
        m = _TEST_ROW_RE.match(ln)
        if m:
            paths.add(m.group(1))
    return paths


def _actual_toplevel_py() -> set[str]:
    return {f'tools/{p.name}' for p in TOOLS.glob('*.py')}


def _actual_test_files() -> set[str]:
    return {f'tools/tests/{p.name}' for p in (TOOLS / 'tests').glob('test_*.py')}


# A numbered-list item whose content starts with a backticked command, e.g.
#   1. `python3 tools/check_converted_py.py .` -- 產物驗證
_CI_STEP_RE = re.compile(r'^\d+\.\s+`([^`]+)`')


def _ci_section() -> list[str]:
    """Lines of the README's `## CI 對應` section."""
    return _section('CI 對應')


def _documented_ci_commands() -> list[str]:
    """Backticked commands from the `## CI 對應` numbered list, in order.

    Anchored to `^\\d+\\.` (after strip) so the inline-code spans in the
    section's prose lines (e.g. ``.github/workflows/...``) are not mistaken for
    steps -- only the numbered list items count.
    """
    cmds: list[str] = []
    for ln in _ci_section():
        m = _CI_STEP_RE.match(ln.strip())
        if m:
            cmds.append(m.group(1))
    return cmds


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


class ReadmeTestTableParityTests(unittest.TestCase):
    """The README "## 測試" table must list exactly the real test_*.py files.

    M20's ReadmeParityTests locked the "## Tools" table against tools/*.py +
    hooks but left the test-file table unguarded -- add / remove / rename a
    test module and the doc silently rots. This is the same parity move,
    applied to tools/tests/.
    """

    def test_tests_table_shape(self):
        # Guards the narrow parser: the 測試 section must contain a markdown
        # table (header separator row) and at least one `tools/tests/...` data
        # row. A reformat away from this shape fails loudly so the parser gets
        # updated rather than silently reading zero test files (mirrors
        # ReadmeParityTests.test_tools_table_shape).
        section = _tests_section()
        self.assertTrue(section, 'no "## 測試" section in README')
        self.assertTrue(
            any(re.match(r'^\|[\s:|-]+\|', ln) for ln in section),
            '測試 section has no markdown table separator row',
        )
        self.assertTrue(
            _documented_test_paths(),
            '測試 table has no `tools/tests/...` rows; update _TEST_ROW_RE',
        )

    def test_all_test_files_documented(self):
        # Core drift guard: documented set == real test_*.py set.
        documented = _documented_test_paths()
        actual = _actual_test_files()
        self.assertEqual(
            documented, actual,
            'tools/README.md "## 測試" table drifted from the real '
            'tools/tests/test_*.py set.\n'
            f'  documented: {sorted(documented)}\n'
            f'  on disk:    {sorted(actual)}\n'
            'Update the "## 測試" table in tools/README.md and the '
            'tools/tests/ tree together.',
        )

    def test_no_undocumented_or_phantom_test_paths(self):
        # Every backticked path in the table must point at a real file (catches
        # typos / a test module documented but never committed).
        for path in sorted(_documented_test_paths()):
            self.assertTrue(
                (REPO / path).exists(),
                f'README 測試 table lists `{path}` but it does not exist',
            )

    def test_test_files_exist_on_disk(self):
        # Positive anchor: parity is only meaningful if both sides describe
        # existing files.
        actual = _actual_test_files()
        self.assertTrue(actual, 'no tools/tests/test_*.py files found')
        for path in sorted(actual):
            self.assertTrue((REPO / path).is_file(), f'missing test file: {path}')


class ReadmeCiParityTests(unittest.TestCase):
    """The README "## CI 對應" numbered list must match the CI workflow steps.

    M18's WorkflowParityTests locks check_all.build_steps() == the workflow yaml
    run-steps, but the README's "## CI 對應" section is a *third* hand-written
    copy of that same ordered step sequence -- change the steps and this doc list
    silently rots. This guard parses the README list, normalizes each command
    with M18's _step_signature, and compares it (in order) against the workflow
    run-commands. Via M18's workflow == build_steps lock this transitively pins
    README == workflow == check_all.
    """

    def test_ci_section_exists(self):
        self.assertTrue(_ci_section(), 'no "## CI 對應" section in README')

    def test_ci_section_shape(self):
        # Guards the narrow parser: the section must contain a numbered list with
        # at least one backticked command. A reformat away from this shape fails
        # loudly so the parser gets updated rather than silently reading zero
        # steps (mirrors test_tools_table_shape / test_tests_table_shape).
        self.assertTrue(
            _documented_ci_commands(),
            'CI 對應 section has no `N. `cmd`` steps; update _CI_STEP_RE',
        )

    def test_ci_step_count_matches_workflow(self):
        self.assertEqual(
            len(_documented_ci_commands()), len(_workflow_run_commands()),
            'README "## CI 對應" lists a different number of steps than the CI '
            'workflow runs.',
        )

    def test_ci_step_signatures_match_workflow_in_order(self):
        # Core drift guard: documented (tool, long_flags) sequence == workflow's.
        doc_sigs = [_step_signature(shlex.split(c)) for c in _documented_ci_commands()]
        wf_sigs = [_step_signature(shlex.split(c)) for c in _workflow_run_commands()]
        self.assertEqual(
            doc_sigs, wf_sigs,
            'tools/README.md "## CI 對應" list drifted from the CI workflow '
            'run-steps.\n'
            f'  README:   {doc_sigs}\n'
            f'  workflow: {wf_sigs}\n'
            'Update the "## CI 對應" section in tools/README.md and '
            '.github/workflows/ipynb-py-sync.yml together (and check_all.py, '
            'which M18 locks to the workflow).',
        )

    def test_ci_tools_in_expected_order(self):
        tools = [_step_signature(shlex.split(c))[0] for c in _documented_ci_commands()]
        self.assertEqual(tools, [
            'unittest',
            'ipynb_to_py.py',
            'check_ipynb_py_sync.py',
            'check_converted_py.py',
        ])

    def test_ci_commands_reference_real_tools(self):
        # Phantom guard: every `.py` script named in the list must exist on disk
        # (catches a typo / a tool documented in the CI list but never committed).
        for cmd in _documented_ci_commands():
            for tok in shlex.split(cmd):
                if tok.endswith('.py'):
                    self.assertTrue(
                        (REPO / tok).exists(),
                        f'README CI list names `{tok}` but it does not exist',
                    )


if __name__ == '__main__':
    unittest.main(verbosity=2)
