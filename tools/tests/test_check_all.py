"""Unit + integration tests for tools/check_all.py.

Stdlib-only unittest. check_all.py is the aggregate entry point that mirrors
the CI workflow (unit tests -> strict pre-scan -> sync check -> converted
check). These tests pin:
  - build_steps()  -- argv construction, ordering, flag plumbing (pure)
  - run_steps()    -- runs every step, no fail-fast (injected runner)
  - main()         -- exit code, progress/summary output (injected runner)
  - CI parity      -- the workflow yaml's run-steps match build_steps() (the
    drift guard for M17's "local == CI" promise; see WorkflowParityTests)
  - docstring parity -- check_all.py's own module docstring lists the 4 CI
    steps a *fourth* time (after the workflow, build_steps, and the README CI
    section); DocstringParityTests locks it == build_steps() so the file's
    self-documentation can't silently rot
  - pre-push parity -- the pre-push hook (M23) runs `check_all.py --skip-tests`
    so a push is gated on CI steps 2-4 (artifact checks minus the unit tests);
    PrePushParityTests locks both that the hook command carries --skip-tests
    (text level) and that build_steps(skip_tests=True) == the workflow's
    run-steps minus the unit-test step
  - trigger parity -- the workflow's `on.push.paths` and `on.pull_request.paths`
    filters are a hand-duplicated pair (and decide *whether* CI runs at all);
    WorkflowTriggerParityTests locks them identical to each other and == the
    canonical trigger set, so a path added/dropped on one side (or silently
    narrowing what re-runs CI) can't rot unnoticed
  - one real-repo integration smoke (rc=0 against the live tree, --skip-tests
    to avoid re-running the whole suite inside a test)

Run:
    python3 tools/tests/test_check_all.py
    # or
    python3 -m unittest tools.tests.test_check_all
"""
from __future__ import annotations

import io
import re
import shlex
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
WORKFLOW = REPO / '.github' / 'workflows' / 'ipynb-py-sync.yml'
PRE_PUSH = TOOLS / 'hooks' / 'pre-push'
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import check_all  # noqa: E402
from check_all import build_steps, main, run_steps  # noqa: E402


class _RecordingRunner:
    """Injectable `run`: records every argv, returns scripted rc per call.

    `rcs` maps a substring -> rc; the first matching substring in the joined
    argv wins. Anything unmatched returns 0 (pass).
    """

    def __init__(self, rcs: dict[str, int] | None = None):
        self.calls: list[list[str]] = []
        self.rcs = rcs or {}

    def __call__(self, argv: list[str]) -> int:
        self.calls.append(argv)
        joined = ' '.join(argv)
        for needle, rc in self.rcs.items():
            if needle in joined:
                return rc
        return 0


def _labels(steps):
    return [label for label, _ in steps]


def _argv(steps, label_substr):
    for label, argv in steps:
        if label_substr in label:
            return argv
    raise AssertionError(f'no step matching {label_substr!r}')


class BuildStepsTests(unittest.TestCase):
    def test_default_builds_four_steps_in_order(self):
        steps = build_steps('.')
        self.assertEqual(len(steps), 4)
        labels = _labels(steps)
        self.assertIn('unit tests', labels[0])
        self.assertIn('strict pre-scan', labels[1])
        self.assertIn('sync check', labels[2])
        self.assertIn('converted check', labels[3])

    def test_skip_tests_drops_unittest_step(self):
        steps = build_steps('.', skip_tests=True)
        self.assertEqual(len(steps), 3)
        self.assertNotIn('unit tests', ' '.join(_labels(steps)))

    def test_first_arg_is_current_interpreter(self):
        for _, argv in build_steps('.'):
            self.assertEqual(argv[0], sys.executable)

    def test_unittest_step_discovers_tools_tests(self):
        argv = _argv(build_steps('.'), 'unit tests')
        self.assertIn('-m', argv)
        self.assertIn('unittest', argv)
        self.assertIn('discover', argv)
        # -s points at the real tools/tests dir, not the scanned root
        self.assertTrue(any(str(TOOLS / 'tests') == a for a in argv))

    def test_prescan_uses_strict_and_dry_run(self):
        argv = _argv(build_steps('myroot'), 'strict pre-scan')
        self.assertIn('--strict', argv)
        self.assertIn('--dry-run', argv)
        self.assertIn('myroot', argv)
        self.assertTrue(argv[1].endswith('ipynb_to_py.py'))

    def test_root_passed_to_checkers(self):
        steps = build_steps('somewhere')
        self.assertIn('somewhere', _argv(steps, 'sync check'))
        self.assertIn('somewhere', _argv(steps, 'converted check'))

    def test_quiet_only_on_checkers_not_prescan(self):
        steps = build_steps('.', quiet=True)
        self.assertIn('--quiet', _argv(steps, 'sync check'))
        self.assertIn('--quiet', _argv(steps, 'converted check'))
        # strict pre-scan has no --quiet flag; must not get one
        self.assertNotIn('--quiet', _argv(steps, 'strict pre-scan'))

    def test_no_quiet_by_default(self):
        steps = build_steps('.')
        self.assertNotIn('--quiet', _argv(steps, 'sync check'))
        self.assertNotIn('--quiet', _argv(steps, 'converted check'))


class RunStepsTests(unittest.TestCase):
    def test_runs_every_step_and_returns_labels(self):
        runner = _RecordingRunner()
        steps = build_steps('.')
        results = run_steps(steps, run=runner)
        self.assertEqual(len(results), 4)
        self.assertEqual(len(runner.calls), 4)
        self.assertTrue(all(rc == 0 for _, rc in results))

    def test_no_fail_fast_runs_all_after_a_failure(self):
        runner = _RecordingRunner({'ipynb_to_py.py': 1})
        steps = build_steps('.')
        results = run_steps(steps, run=runner)
        # all four still invoked despite step 2 failing
        self.assertEqual(len(runner.calls), 4)
        rcs = {label: rc for label, rc in results}
        self.assertEqual(rcs['strict pre-scan (parse, no write)'], 1)

    def test_preserves_step_order(self):
        runner = _RecordingRunner()
        steps = build_steps('.')
        run_steps(steps, run=runner)
        ran = [' '.join(c) for c in runner.calls]
        self.assertIn('unittest', ran[0])
        self.assertIn('ipynb_to_py.py', ran[1])
        self.assertIn('check_ipynb_py_sync.py', ran[2])
        self.assertIn('check_converted_py.py', ran[3])


class MainTests(unittest.TestCase):
    def _run_main(self, argv, runner):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(argv, run=runner)
        return rc, buf.getvalue()

    def test_all_pass_returns_zero(self):
        runner = _RecordingRunner()
        rc, out = self._run_main(['.'], runner)
        self.assertEqual(rc, 0)
        self.assertIn('All 4 step(s) passed.', out)
        self.assertEqual(out.count('PASS'), 4)

    def test_any_failure_returns_one(self):
        runner = _RecordingRunner({'check_converted_py.py': 2})
        rc, out = self._run_main(['.'], runner)
        self.assertEqual(rc, 1)
        self.assertIn('FAIL', out)
        self.assertIn('1/4 step(s) FAILED', out)
        self.assertIn('converted check (compile + no magic leaks)', out)

    def test_multiple_failures_listed(self):
        runner = _RecordingRunner({'ipynb_to_py.py': 1, 'check_converted_py.py': 2})
        rc, out = self._run_main(['.'], runner)
        self.assertEqual(rc, 1)
        self.assertIn('2/4 step(s) FAILED', out)

    def test_skip_tests_runs_three_steps(self):
        runner = _RecordingRunner()
        rc, out = self._run_main(['--skip-tests', '.'], runner)
        self.assertEqual(rc, 0)
        self.assertEqual(len(runner.calls), 3)
        self.assertIn('[1/3]', out)
        self.assertNotIn('unittest', ' '.join(' '.join(c) for c in runner.calls))

    def test_quiet_flag_plumbed_to_checkers(self):
        runner = _RecordingRunner()
        self._run_main(['--quiet', '.'], runner)
        joined = [' '.join(c) for c in runner.calls]
        sync = next(c for c in joined if 'check_ipynb_py_sync.py' in c)
        conv = next(c for c in joined if 'check_converted_py.py' in c)
        self.assertIn('--quiet', sync)
        self.assertIn('--quiet', conv)

    def test_progress_header_counts_total(self):
        runner = _RecordingRunner()
        _, out = self._run_main(['.'], runner)
        self.assertIn('[1/4]', out)
        self.assertIn('[4/4]', out)


class IntegrationTests(unittest.TestCase):
    """Run the real steps against the live repo (rc must be 0).

    Uses --skip-tests so we don't recursively re-run the whole unittest suite
    inside one of its own tests; this still exercises the converter pre-scan
    and both checkers end-to-end against the real 77-notebook tree.
    """

    def test_repo_passes_all_non_test_steps(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main(['--skip-tests', '--quiet', str(REPO)])
        out = buf.getvalue()
        self.assertEqual(rc, 0, msg=f'check_all reported failure:\n{out}')
        self.assertIn('All 3 step(s) passed.', out)


# --- CI parity (drift guard) -------------------------------------------------
# M17 built check_all.py to mirror .github/workflows/ipynb-py-sync.yml
# "step-for-step", but nothing enforced that the two stay aligned: edit the
# workflow (add/drop/reorder a step, drop --strict) without touching check_all
# and the "local == CI" promise silently rots. These tests lock that invariant
# in -- same precedent as M9 (orphan detection) / M14 (sync-checker main paths):
# a thing that was only true by convention becomes true by test.

# Single-dash display flags that legitimately differ between the CI yaml (which
# wants verbose output in the Actions log) and check_all's argv. Normalized away
# so they don't register as drift.
_DISPLAY_ONLY_FLAGS = {'-v', '--verbose'}


def _step_signature(tokens: list[str]) -> tuple[str | None, frozenset[str]]:
    """Reduce one command's tokens to its meaningful contract.

    Returns ``(tool, frozenset(long_flags))`` where *tool* is ``'unittest'`` or
    the basename of the invoked ``.py`` script, and *long_flags* are the
    ``--`` flags that change behaviour. Deliberately ignores: the interpreter
    name, any path prefix on the script (``tools/foo.py`` vs an absolute path),
    the trailing root arg (``.`` / a temp dir), single-dash flags and their
    values (``-s tools/tests``), and display-only ``-v``. What survives is
    exactly what must match between CI and check_all for "local == CI" to hold.
    """
    tool: str | None = None
    flags: set[str] = set()
    for tok in tokens:
        if tok in _DISPLAY_ONLY_FLAGS:
            continue
        if tok == 'unittest':
            tool = 'unittest'
        elif tok.endswith('.py'):
            tool = Path(tok).name
        elif tok.startswith('--'):
            flags.add(tok)
    return (tool, frozenset(flags))


def _workflow_run_commands() -> list[str]:
    """Ordered list of single-line `run:` commands from the workflow yaml.

    Stdlib-only (no PyYAML -- system Python is PEP 668 locked). Assumes every
    `run:` is a one-line scalar; multiline `run: |` blocks would need a real
    parser, so WorkflowParityTests asserts none exist before relying on this.
    """
    cmds: list[str] = []
    for line in WORKFLOW.read_text().splitlines():
        m = re.match(r'\s*run:\s*(\S.*?)\s*$', line)
        if m:
            cmds.append(m.group(1))
    return cmds


def _docstring_step_commands() -> list[str]:
    """Ordered `python3 ...` commands from the numbered step list in
    check_all.py's module docstring.

    That docstring restates the CI step sequence a *fourth* time -- a
    hand-written copy alongside the workflow yaml, build_steps(), and the
    README "## CI 對應" section. This parser lets DocstringParityTests lock it
    == build_steps() the same way WorkflowParityTests (M18) locks the workflow
    yaml and ReadmeCiParityTests (M22) locks the README list. Each step line
    looks like:

        1. unit tests       python3 -m unittest discover -s tools/tests

    so we grab the trailing `python3 ...` command and ignore the label.
    """
    cmds: list[str] = []
    for line in (check_all.__doc__ or '').splitlines():
        m = re.match(r'\s*\d+\.\s+.*?(python3\s+\S.*?)\s*$', line)
        if m:
            cmds.append(m.group(1).strip())
    return cmds


class DocstringParityTests(unittest.TestCase):
    """Lock check_all.py's module-docstring step list == build_steps().

    Same precedent as WorkflowParityTests (M18) / ReadmeCiParityTests (M22):
    a hand-written copy of the CI step sequence that holds only by convention
    becomes true by test. Reuses _step_signature so the docstring is compared
    by the same normalized (tool, long_flags) contract as the workflow and
    build_steps -- transitively closing the loop docstring == build_steps ==
    workflow == README.
    """

    def test_docstring_lists_four_numbered_commands(self):
        # Guards the parser assumption: if someone reformats the docstring out
        # of the "N. label  python3 ..." shape, fail loudly here rather than
        # silently parsing zero commands and passing the parity tests vacuously.
        cmds = _docstring_step_commands()
        self.assertEqual(
            len(cmds), 4,
            f'expected 4 numbered python3 steps in check_all docstring, got {cmds!r}',
        )

    def test_docstring_step_count_matches_build_steps(self):
        self.assertEqual(len(_docstring_step_commands()), len(build_steps('.')))

    def test_docstring_signatures_match_build_steps_in_order(self):
        doc_sigs = [_step_signature(shlex.split(c)) for c in _docstring_step_commands()]
        build_sigs = [_step_signature(argv) for _, argv in build_steps('.')]
        self.assertEqual(
            doc_sigs, build_sigs,
            "check_all.py's module docstring drifted from build_steps().\n"
            f'  docstring:  {doc_sigs}\n'
            f'  build_steps:{build_sigs}\n'
            'Update the numbered step list in tools/check_all.py docstring to '
            'match build_steps() (and keep both aligned with the CI workflow).',
        )

    def test_docstring_tools_in_expected_order(self):
        tools = [_step_signature(shlex.split(c))[0] for c in _docstring_step_commands()]
        self.assertEqual(tools, [
            'unittest',
            'ipynb_to_py.py',
            'check_ipynb_py_sync.py',
            'check_converted_py.py',
        ])

    def test_docstring_strict_dry_run_gate_present(self):
        prescan = next(
            _step_signature(shlex.split(c)) for c in _docstring_step_commands()
            if 'ipynb_to_py.py' in c
        )
        self.assertEqual(prescan[0], 'ipynb_to_py.py')
        self.assertIn('--strict', prescan[1])
        self.assertIn('--dry-run', prescan[1])

    def test_docstring_matches_workflow_transitively(self):
        # docstring == workflow follows from docstring == build_steps (above)
        # and build_steps == workflow (WorkflowParityTests), but asserting it
        # directly pins the closed loop and gives a clearer failure if the
        # docstring is the side that drifted.
        doc_sigs = [_step_signature(shlex.split(c)) for c in _docstring_step_commands()]
        wf_sigs = [_step_signature(shlex.split(c)) for c in _workflow_run_commands()]
        self.assertEqual(doc_sigs, wf_sigs)


class WorkflowParityTests(unittest.TestCase):
    def test_workflow_file_exists(self):
        self.assertTrue(WORKFLOW.is_file(), f'missing CI workflow: {WORKFLOW}')

    def test_no_multiline_run_blocks(self):
        # Guards the single-line assumption in _workflow_run_commands(). If
        # someone converts a step to `run: |`, fail loudly (update the parser)
        # rather than silently mis-reading it as an empty command.
        bad = [ln for ln in WORKFLOW.read_text().splitlines()
               if re.match(r'\s*run:\s*[|>]\s*$', ln)]
        self.assertEqual(bad, [], 'multiline run: block found; update the parser')

    def test_run_step_count_matches_build_steps(self):
        self.assertEqual(len(_workflow_run_commands()), len(build_steps('.')))

    def test_step_signatures_match_in_order(self):
        wf_sigs = [_step_signature(shlex.split(c)) for c in _workflow_run_commands()]
        build_sigs = [_step_signature(argv) for _, argv in build_steps('.')]
        self.assertEqual(
            wf_sigs, build_sigs,
            'check_all.build_steps() drifted from the CI workflow run-steps.\n'
            f'  workflow:   {wf_sigs}\n'
            f'  build_steps:{build_sigs}\n'
            'Update tools/check_all.py and .github/workflows/ipynb-py-sync.yml '
            'together so local == CI.',
        )

    def test_tools_invoked_in_expected_order(self):
        tools = [_step_signature(shlex.split(c))[0] for c in _workflow_run_commands()]
        self.assertEqual(tools, [
            'unittest',
            'ipynb_to_py.py',
            'check_ipynb_py_sync.py',
            'check_converted_py.py',
        ])

    def test_strict_dry_run_gate_present_in_both(self):
        # M16's CI strict pre-scan must stay wired on both sides.
        wf_prescan = next(
            _step_signature(shlex.split(c)) for c in _workflow_run_commands()
            if 'ipynb_to_py.py' in c
        )
        self.assertEqual(wf_prescan[0], 'ipynb_to_py.py')
        self.assertIn('--strict', wf_prescan[1])
        self.assertIn('--dry-run', wf_prescan[1])
        build_prescan = _step_signature(_argv(build_steps('.'), 'strict pre-scan'))
        self.assertEqual(wf_prescan, build_prescan)


# --- pre-push parity (drift guard) -------------------------------------------
# The pre-push hook (M23) runs `check_all.py --skip-tests` so a push is gated on
# the same artifact checks CI runs minus the unit-test step. Two invariants held
# only by convention until M27:
#   1. the hook command actually carries --skip-tests. PrePushHookTests does
#      exercise the hook end-to-end, but it only catches a dropped --skip-tests
#      *incidentally*: its fixture has no tools/tests/ dir, so a full check_all's
#      `unittest discover -s tools/tests` raises ImportError (rc != 0) and the
#      push-blocks. That is fragile -- the failure is an opaque "Start directory
#      is not importable" with no hint the real cause is a missing flag, and if
#      the fixture ever contained an empty tools/tests/, discover would find 0
#      tests (rc 0) and the drop would pass undetected. A direct text-level
#      assertion catches it intentionally, with an actionable message.
#   2. build_steps(skip_tests=True) == "CI steps 2-4" (the hook docstring's
#      claim) == the workflow's run-steps minus the single unit-test step. No
#      existing test ties skip_tests to the workflow; M18 only locks the full
#      build_steps == workflow.
# Same precedent as M18 (workflow parity) / M22 (README CI list) / M26 (docstring):
# a hand-written contract that held by convention becomes true by test. Reuses
# the M18 _step_signature / _workflow_run_commands normalization throughout.


def _prepush_check_all_tokens() -> list[str]:
    """shlex tokens of the check_all.py invocation inside the pre-push hook.

    The hook line looks like ``if ! python3 tools/check_all.py --skip-tests; then``;
    we strip the ``if ! `` guard and trailing ``; then`` and split the rest so
    the flags the hook actually passes can be asserted at the text level.
    """
    for line in PRE_PUSH.read_text().splitlines():
        if 'check_all.py' in line and 'python3' in line:
            cmd = line.strip()
            cmd = re.sub(r'^if\s+!\s+', '', cmd)
            cmd = re.sub(r'\s*;\s*then\s*$', '', cmd)
            return shlex.split(cmd)
    raise AssertionError('pre-push hook does not invoke python3 ... check_all.py')


class PrePushParityTests(unittest.TestCase):
    def test_pre_push_hook_exists(self):
        self.assertTrue(PRE_PUSH.is_file(), f'missing pre-push hook: {PRE_PUSH}')

    def test_hook_invokes_check_all(self):
        toks = _prepush_check_all_tokens()
        self.assertTrue(
            any(t.endswith('check_all.py') for t in toks),
            f'pre-push hook should run check_all.py, got {toks!r}',
        )

    def test_hook_passes_skip_tests(self):
        toks = _prepush_check_all_tokens()
        self.assertIn(
            '--skip-tests', toks,
            'pre-push hook must run check_all.py --skip-tests; without it the '
            'hook re-runs the whole unit-test suite on every push (the behaviour '
            'its docstring says is intentionally avoided). The integration '
            'PrePushHookTests only catches this incidentally (its fixture has no '
            'tools/tests/, so discover raises ImportError); this guard catches it '
            'directly at the text level.',
        )

    def test_hook_carries_only_skip_tests(self):
        # --skip-tests is the only behaviour flag the hook should pass; a stray
        # --quiet (or anything else) would silently change what a push is gated on.
        toks = _prepush_check_all_tokens()
        long_flags = {t for t in toks if t.startswith('--')}
        self.assertEqual(long_flags, {'--skip-tests'})

    def test_skip_tests_drops_exactly_the_first_step(self):
        full = [_step_signature(argv) for _, argv in build_steps('.')]
        skipped = [_step_signature(argv) for _, argv in build_steps('.', skip_tests=True)]
        self.assertEqual(
            skipped, full[1:],
            'skip_tests must drop exactly the first step and keep steps 2-4 in order.',
        )

    def test_dropped_step_is_the_unittest_one(self):
        first_label, first_argv = build_steps('.')[0]
        self.assertIn('unit tests', first_label)
        self.assertEqual(_step_signature(first_argv)[0], 'unittest')

    def test_skip_tests_steps_match_workflow_minus_unittest(self):
        # Ties the hook docstring's "CI steps 2-4" claim directly to the workflow:
        # build_steps(skip_tests=True) == the workflow run-steps after dropping
        # the single unit-test step. Reuses the M18 normalization so this is the
        # same contract as WorkflowParityTests, just on the artifact subset.
        wf_sigs = [_step_signature(shlex.split(c)) for c in _workflow_run_commands()]
        wf_artifact = [s for s in wf_sigs if s[0] != 'unittest']
        self.assertEqual(
            len(wf_sigs) - len(wf_artifact), 1,
            'expected exactly one unit-test step in the workflow to drop',
        )
        skipped = [_step_signature(argv) for _, argv in build_steps('.', skip_tests=True)]
        self.assertEqual(skipped, wf_artifact)


# --- trigger parity (drift guard) --------------------------------------------
# M18/M22/M26/M27 locked the workflow's *run-steps* (what CI does) against
# build_steps / README / docstring / pre-push. But the workflow also has a
# `paths:` trigger filter -- written out twice, once under `on.push` and once
# under `on.pull_request` -- that decides *whether the sync CI runs at all*.
# Nothing guards those two hand-maintained copies: add a path to one and forget
# the other and push-vs-PR silently cover different file sets; drop `**/*.ipynb`
# or `tools/**` by accident and CI quietly stops re-running on the very changes
# it exists to catch (a far more dangerous "green" than a failing step). Same
# precedent as every parity guard since M18 -- a duplicate held by convention
# becomes true by test. Stdlib-only line parser (PyYAML is PEP 668 locked);
# the tests pin the structural shape it assumes.

# The canonical set of paths that must trigger the sync CI. Adding a genuinely
# new trigger path is a deliberate act -- update this set in the same commit so
# the lock stays meaningful (same convention as M21's README test-table lock).
_EXPECTED_TRIGGER_PATHS = [
    '**/*.ipynb',
    '**/*.py',
    'tools/**',
    '.github/workflows/ipynb-py-sync.yml',
]


def _workflow_trigger_paths() -> dict[str, list[str]]:
    """Parse on.<event>.paths lists from the workflow yaml (stdlib only).

    Returns ``{event: [path, ...]}`` for each of ``push`` / ``pull_request``
    that declares a ``paths:`` filter, quotes stripped, order preserved.
    Assumes the two-level ``on: -> <event>: -> paths:`` shape this workflow
    uses (event header at 2-space indent, ``paths:`` at 4, items deeper). A
    structural change (paths-ignore, a multiline list, reindent) yields a
    different/empty parse, which WorkflowTriggerParityTests catches by pinning
    the expected shape -- fail loudly, update the parser, never mis-read.
    """
    result: dict[str, list[str]] = {}
    event: str | None = None
    in_paths = False
    paths_indent = -1
    for line in WORKFLOW.read_text().splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        m_event = re.match(r'(push|pull_request):\s*$', stripped)
        if m_event and indent == 2:
            event = m_event.group(1)
            in_paths = False
            continue
        if event and indent == 4 and re.match(r'paths:\s*$', stripped):
            in_paths = True
            paths_indent = indent
            result.setdefault(event, [])
            continue
        if in_paths:
            m_item = re.match(r'-\s*(\S.*?)\s*$', stripped)
            if m_item and indent > paths_indent:
                result[event].append(m_item.group(1).strip().strip('\'"'))
                continue
            in_paths = False
    return result


class WorkflowTriggerParityTests(unittest.TestCase):
    def test_both_events_declare_paths(self):
        paths = _workflow_trigger_paths()
        self.assertIn('push', paths, 'on.push.paths not found (parser or yaml drift)')
        self.assertIn('pull_request', paths,
                      'on.pull_request.paths not found (parser or yaml drift)')
        self.assertTrue(paths['push'], 'on.push.paths parsed empty')
        self.assertTrue(paths['pull_request'], 'on.pull_request.paths parsed empty')

    def test_push_and_pull_request_paths_identical(self):
        # The core guard: the two hand-duplicated filters must not drift.
        paths = _workflow_trigger_paths()
        self.assertEqual(
            paths['push'], paths['pull_request'],
            'on.push.paths and on.pull_request.paths drifted apart.\n'
            f'  push:         {paths["push"]}\n'
            f'  pull_request: {paths["pull_request"]}\n'
            'A change to one trigger filter was not mirrored on the other, so '
            'push and PR builds now run on different file sets. Edit both in '
            '.github/workflows/ipynb-py-sync.yml together.',
        )

    def test_trigger_paths_match_expected_set(self):
        # Locks the trigger surface so silently narrowing it (dropping a glob)
        # -- which makes CI quietly stop running on relevant changes -- fails.
        paths = _workflow_trigger_paths()
        self.assertEqual(
            paths['push'], _EXPECTED_TRIGGER_PATHS,
            'workflow trigger paths drifted from the canonical set.\n'
            f'  workflow: {paths["push"]}\n'
            f'  expected: {_EXPECTED_TRIGGER_PATHS}\n'
            'If this change is intentional, update _EXPECTED_TRIGGER_PATHS in '
            'this test in the same commit.',
        )

    def test_notebook_and_py_globs_present(self):
        # The two artifact globs are why this CI exists: a .ipynb or .py edit
        # must re-run the sync/converted checks.
        push = _workflow_trigger_paths()['push']
        self.assertIn('**/*.ipynb', push)
        self.assertIn('**/*.py', push)

    def test_tools_dir_triggers_ci(self):
        # A change to any tool / test / hook under tools/ must re-run CI -- the
        # checks' own logic lives there.
        self.assertIn('tools/**', _workflow_trigger_paths()['push'])

    def test_workflow_self_referenced_in_paths(self):
        # Editing the workflow itself must re-trigger it; assert its own
        # repo-relative path is in the filter (computed, not hard-coded).
        rel = str(WORKFLOW.relative_to(REPO)).replace('\\', '/')
        self.assertIn(rel, _workflow_trigger_paths()['push'],
                      f'workflow does not list its own path {rel!r} as a trigger')


if __name__ == '__main__':
    unittest.main(verbosity=2)
