"""Unit + integration tests for tools/check_all.py.

Stdlib-only unittest. check_all.py is the aggregate entry point that mirrors
the CI workflow (unit tests -> strict pre-scan -> sync check -> converted
check). These tests pin:
  - build_steps()  -- argv construction, ordering, flag plumbing (pure)
  - run_steps()    -- runs every step, no fail-fast (injected runner)
  - main()         -- exit code, progress/summary output (injected runner)
  - one real-repo integration smoke (rc=0 against the live tree, --skip-tests
    to avoid re-running the whole suite inside a test)

Run:
    python3 tools/tests/test_check_all.py
    # or
    python3 -m unittest tools.tests.test_check_all
"""
from __future__ import annotations

import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
REPO = TOOLS.parent
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


if __name__ == '__main__':
    unittest.main(verbosity=2)
