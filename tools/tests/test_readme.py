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
  - ReadmeCiTriggerParityTests -- "## CI 對應" intro trigger paths
                                  vs  workflow on.push/pull_request paths (M30)
  - InstallParityTests         -- install.sh loop + README `ln -sf` block
                                  vs  tools/hooks/ scripts on disk (M24)

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
from test_check_all import (  # noqa: E402
    WORKFLOW,
    _step_signature,
    _workflow_run_commands,
    _workflow_trigger_paths,
)

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


# Any inline `code span` in a markdown section, used to harvest the trigger-path
# tokens the README's "## CI 對應" intro cites in prose.
_BACKTICK_SPAN_RE = re.compile(r'`([^`]+)`')


def _display_trigger(tok: str) -> str | None:
    """Normalize one path token to its user-facing trigger form, or None.

    The workflow `paths:` list and the README "## CI 對應" intro are two
    hand-written copies of the same trigger surface written in *different*
    notations: the workflow uses globs (`**/*.ipynb`, `tools/**`) while the
    README cites the user-friendly extension form (`.ipynb`, `tools/**`). This
    maps both onto a single canonical display token so the two copies can be
    compared deterministically:

      - `**/*.ipynb` / `**/*.py`  -> `.ipynb` / `.py`  (strip the `**/*` glob)
      - `tools/**` (and any `*/**`) -> itself
      - a bare extension `.ipynb` / `.py`               -> itself

    Everything else -- bare filenames (`check_all.py`), command words
    (`python3`, `tools/tests`), the root arg `.`, and the workflow
    self-reference path `.github/workflows/ipynb-py-sync.yml` -- returns None so
    it is excluded from the trigger set on both sides. The self-reference path
    is intentionally not part of the *user-facing* surface (the README cites the
    workflow file as the subject of the sentence, not as a watched path), and
    dropping it on both sides keeps the comparison honest.
    """
    if tok.startswith('**/*'):
        return tok[len('**/*'):] or None
    if tok.endswith('/**'):
        return tok
    if re.fullmatch(r'\.\w+', tok):
        return tok
    return None


def _documented_ci_trigger_tokens() -> set[str]:
    """Display-normalized trigger tokens cited in the README "## CI 對應" section.

    Harvests every inline `code span` in the section, splits each on whitespace
    (so a multi-word command span like `python3 -m unittest ...` contributes its
    individual tokens), and keeps only those _display_trigger recognizes.
    """
    tokens: set[str] = set()
    for span in _BACKTICK_SPAN_RE.findall('\n'.join(_ci_section())):
        for tok in span.split():
            disp = _display_trigger(tok)
            if disp:
                tokens.add(disp)
    return tokens


def _workflow_trigger_display() -> set[str]:
    """Display-normalized trigger set from the workflow's push `paths:` list.

    push == pull_request is already locked by M29's WorkflowTriggerParityTests,
    so either copy is a valid source of truth; push is used here.
    """
    push = _workflow_trigger_paths().get('push', [])
    return {d for d in (_display_trigger(p) for p in push) if d}


INSTALL_SH = TOOLS / 'hooks' / 'install.sh'
HOOKS_DIR = TOOLS / 'hooks'

# `for hook in pre-commit pre-push; do` in install.sh
_INSTALL_LOOP_RE = re.compile(r'^\s*for\s+hook\s+in\s+(.+?)\s*;\s*do\s*$')
# `ln -sf ../../tools/hooks/<hook> .git/hooks/<hook>` in the README manual block;
# capture both the symlink source basename and the destination basename.
_LN_SF_RE = re.compile(r'ln\s+-sf\s+\S*tools/hooks/(\S+)\s+\S*\.git/hooks/(\S+)')


def _install_sh_loop_hooks() -> set[str]:
    """Hook names from install.sh's `for hook in ...; do` loop."""
    for ln in INSTALL_SH.read_text(encoding='utf-8').splitlines():
        m = _INSTALL_LOOP_RE.match(ln)
        if m:
            return set(m.group(1).split())
    return set()


def _manual_install_lines() -> list[tuple[str, str]]:
    """(src_basename, dst_basename) pairs from the README manual `ln -sf` lines.

    Scoped to the "## 安裝 git hooks" section so unrelated `ln -sf` examples
    elsewhere in the README cannot leak in.
    """
    pairs: list[tuple[str, str]] = []
    for ln in _section('安裝 git hooks'):
        m = _LN_SF_RE.search(ln)
        if m:
            pairs.append((m.group(1), m.group(2)))
    return pairs


def _manual_install_hooks() -> set[str]:
    """Hook names symlinked by the README manual `ln -sf` block."""
    return {src for src, _dst in _manual_install_lines()}


def _disk_installable_hooks() -> set[str]:
    """Executable hook scripts install.sh installs: every file in tools/hooks/
    except the installer itself (the source of truth for the hook set)."""
    return {
        p.name for p in HOOKS_DIR.iterdir()
        if p.is_file() and p.name != 'install.sh'
    }


def _disk_all_hook_scripts() -> set[str]:
    """Every `tools/hooks/...` script on disk (installer included)."""
    return {f'tools/hooks/{p.name}' for p in HOOKS_DIR.iterdir() if p.is_file()}


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


class ReadmeCiTriggerParityTests(unittest.TestCase):
    """The README "## CI 對應" intro must cite the workflow's trigger surface.

    M22's ReadmeCiParityTests locks the README's *numbered run-step list*
    against the workflow run-steps, and M29's WorkflowTriggerParityTests locks
    the workflow's two `paths:` copies (push == pull_request == canonical). But
    the README "## CI 對應" *intro sentence* is yet another hand-written copy of
    the same trigger surface -- "在 push / PR 觸碰 `.ipynb` / `.py` / `tools/**`
    時跑" -- that no test guards. Drop `tools/**` from the workflow paths (or add
    a new trigger glob) and this prose silently rots, misleading anyone who
    reads the doc to understand when CI fires. This is the same parity move as
    M22 / M29, applied to the doc's trigger description: the README's cited
    trigger tokens, display-normalized, must equal the workflow's. Via M29's
    push == pull_request == canonical lock this transitively pins README ==
    workflow == canonical for the trigger filter too.
    """

    def test_ci_section_cites_trigger_paths(self):
        # Guards the narrow harvester: the section must cite at least one
        # recognizable trigger token. A reword that drops every backticked path
        # fails loudly so the harvester / regex gets revisited rather than
        # silently comparing two empty sets (mirrors the *_shape guards above).
        self.assertTrue(
            _documented_ci_trigger_tokens(),
            'CI 對應 intro cites no trigger paths; update _display_trigger / '
            'the README prose',
        )

    def test_workflow_exposes_trigger_paths(self):
        # Positive anchor: parity is only meaningful if the workflow side is
        # non-empty too (M29 owns the deep structural checks).
        self.assertTrue(
            _workflow_trigger_display(),
            'workflow declares no display-able trigger paths; '
            'check _workflow_trigger_paths',
        )

    def test_documented_triggers_match_workflow(self):
        # Core drift guard: README trigger tokens == workflow trigger surface.
        doc = _documented_ci_trigger_tokens()
        wf = _workflow_trigger_display()
        self.assertEqual(
            doc, wf,
            'tools/README.md "## CI 對應" intro drifted from the CI workflow '
            'trigger `paths:`.\n'
            f'  README cites: {sorted(doc)}\n'
            f'  workflow:     {sorted(wf)}\n'
            'Update the "## CI 對應" intro sentence in tools/README.md and the '
            'on.push/on.pull_request paths in .github/workflows/'
            'ipynb-py-sync.yml together (M29 locks the two workflow copies).',
        )

    def test_notebook_and_py_globs_documented(self):
        # The two artifact globs are the reason this CI exists; the doc must name
        # both so a reader knows notebook+sibling changes trigger it.
        doc = _documented_ci_trigger_tokens()
        for tok in ('.ipynb', '.py'):
            self.assertIn(
                tok, doc,
                f'README CI 對應 intro must cite the `{tok}` trigger',
            )

    def test_tools_dir_documented(self):
        # Toolchain edits must (and the doc must say they) re-run CI.
        self.assertIn(
            'tools/**', _documented_ci_trigger_tokens(),
            'README CI 對應 intro must cite the `tools/**` trigger',
        )

    def test_workflow_self_reference_not_user_facing(self):
        # Documents the intentional asymmetry: the workflow watches its own file
        # (M29 test_workflow_self_referenced_in_paths), but that is an internal
        # detail, not part of the user-facing trigger surface -- so it is absent
        # from both display sets. Guards against someone "fixing" the doc by
        # listing the workflow path as a watched glob (which _display_trigger
        # would then have to start surfacing).
        self_ref = str(WORKFLOW.relative_to(REPO))
        self.assertIsNone(
            _display_trigger(self_ref),
            f'{self_ref} should not normalize to a user-facing trigger token',
        )
        self.assertNotIn(self_ref, _documented_ci_trigger_tokens())
        self.assertNotIn(self_ref, _workflow_trigger_display())


class InstallParityTests(unittest.TestCase):
    """The git-hook *set* must agree across its four hand-written copies.

    After M23 "which hooks does the toolchain install" is written in four
    places: the real scripts in tools/hooks/ (source of truth), install.sh's
    `for hook in ...` loop, the README "## Tools" table (M20-guarded, but via
    the *hardcoded* _HOOK_PATHS constant), and the README "## 安裝 git hooks"
    manual `ln -sf` block (until now unguarded). Add a hook and forget the loop
    or the manual block and it silently rots -- the same "true only by
    convention" gap M18 / M20 / M21 / M22 each closed by locking the invariant
    into a test. These pin install.sh's loop and the README manual block to the
    real hook set on disk, and validate the hardcoded _HOOK_PATHS against disk.
    """

    def test_install_sh_loop_shape(self):
        # Guards the narrow parser: install.sh must contain a parseable
        # `for hook in ...; do` loop. A refactor away from this shape fails
        # loudly so the parser gets updated rather than reading zero hooks.
        self.assertTrue(
            _install_sh_loop_hooks(),
            'install.sh has no `for hook in ...; do` loop; update _INSTALL_LOOP_RE',
        )

    def test_manual_install_block_shape(self):
        # Guards the narrow parser: the 安裝 section must have at least one
        # `ln -sf .../tools/hooks/<hook> .../.git/hooks/<hook>` line.
        self.assertTrue(
            _manual_install_hooks(),
            'README "## 安裝 git hooks" has no `ln -sf` hook lines; '
            'update _LN_SF_RE',
        )

    def test_install_sh_hooks_match_disk(self):
        # Core drift guard: install.sh's loop installs exactly the hook scripts
        # that exist in tools/hooks/ (installer excluded).
        loop = _install_sh_loop_hooks()
        disk = _disk_installable_hooks()
        self.assertEqual(
            loop, disk,
            "install.sh's `for hook in ...` loop drifted from the real "
            'tools/hooks/ scripts.\n'
            f'  install.sh loop: {sorted(loop)}\n'
            f'  on disk:         {sorted(disk)}\n'
            'Update the loop in tools/hooks/install.sh and the tools/hooks/ '
            'tree together.',
        )

    def test_manual_install_hooks_match_disk(self):
        # Core drift guard: the README manual `ln -sf` block symlinks exactly
        # the hook scripts that exist on disk.
        manual = _manual_install_hooks()
        disk = _disk_installable_hooks()
        self.assertEqual(
            manual, disk,
            'README "## 安裝 git hooks" manual `ln -sf` block drifted from the '
            'real tools/hooks/ scripts.\n'
            f'  README manual: {sorted(manual)}\n'
            f'  on disk:       {sorted(disk)}\n'
            'Update the manual install block in tools/README.md and the '
            'tools/hooks/ tree together.',
        )

    def test_install_sh_and_manual_block_agree(self):
        # Transitive sanity: the two hand-written copies equal each other
        # directly (each is also pinned to disk above; this gives a clearer
        # message when only those two -- not disk -- diverge).
        self.assertEqual(
            _install_sh_loop_hooks(), _manual_install_hooks(),
            "install.sh's loop and the README manual `ln -sf` block list "
            'different hook sets.',
        )

    def test_manual_install_symlink_src_equals_dst(self):
        # Each manual line must symlink tools/hooks/<h> to .git/hooks/<h> with a
        # matching basename -- a mismatched dst would install a broken hook.
        for src, dst in _manual_install_lines():
            self.assertEqual(
                src, dst,
                f'README manual `ln -sf` maps tools/hooks/{src} to '
                f'.git/hooks/{dst}; basenames must match',
            )

    def test_hook_paths_constant_matches_disk(self):
        # Validate M20's hardcoded _HOOK_PATHS against disk so the "## Tools"
        # table guard (test_hook_scripts_documented) can't be silently bypassed
        # by a hook that exists but was never added to the constant.
        self.assertEqual(
            _HOOK_PATHS, _disk_all_hook_scripts(),
            'test_readme._HOOK_PATHS drifted from the real tools/hooks/ tree.\n'
            f'  constant: {sorted(_HOOK_PATHS)}\n'
            f'  on disk:  {sorted(_disk_all_hook_scripts())}\n'
            'Update _HOOK_PATHS and the README "## Tools" table together.',
        )


if __name__ == '__main__':
    unittest.main(verbosity=2)
