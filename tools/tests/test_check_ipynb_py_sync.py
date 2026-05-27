"""Unit tests for tools/check_ipynb_py_sync.py.

Stdlib-only unittest. M9 covered the orphan-detection helper
(``_orphan_py``); M14 closes the remaining gap by pinning the rest of
the checker — ``_pairs`` (notebook discovery), ``_diff_preview`` (drift
rendering), and ``main`` (the in-sync / missing / drift / error / orphan
exit paths). This brings the sync checker to main()-level coverage parity
with the converter (M13) and the converted-py validator (M10), so all
four CLI tools in the toolchain now have unit-tested entry points.

Run:
    python3 tools/tests/test_check_ipynb_py_sync.py
    # or
    python3 -m unittest tools.tests.test_check_ipynb_py_sync
"""
from __future__ import annotations

import io
import json
import re
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from check_ipynb_py_sync import (  # noqa: E402
    _diff_preview,
    _orphan_py,
    _pairs,
    main,
)
from ipynb_to_py import convert_to_str  # noqa: E402


def _touch(path: Path, content: str = '') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _nb(path: Path) -> Path:
    nb = {'cells': [], 'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}
    return _touch(path, json.dumps(nb))


def _synced_pair(path: Path) -> tuple[Path, Path]:
    """Create an .ipynb and write its byte-for-byte matching .py sibling."""
    nb = _nb(path)
    py = nb.with_suffix('.py')
    py.write_text(convert_to_str(nb), encoding='utf-8')
    return nb, py


class OrphanPyTests(unittest.TestCase):
    """Cover every branch of _orphan_py without touching the real repo."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_empty_tree_returns_no_orphans(self) -> None:
        self.assertEqual(_orphan_py(self.root), [])

    def test_matched_pair_is_not_orphan(self) -> None:
        _nb(self.root / 'Foo.ipynb')
        _touch(self.root / 'Foo.py', '# converted')
        self.assertEqual(_orphan_py(self.root), [])

    def test_unmatched_py_at_root_is_orphan(self) -> None:
        _touch(self.root / 'orphan.py', '# no notebook')
        self.assertEqual(_orphan_py(self.root), [Path('orphan.py')])

    def test_unmatched_py_in_subdir_is_orphan(self) -> None:
        _touch(self.root / 'example' / 'gone.py', '# stale')
        self.assertEqual(_orphan_py(self.root), [Path('example/gone.py')])

    def test_tools_py_is_never_orphan(self) -> None:
        """Handwritten tooling under tools/ has no matching .ipynb by design."""
        _touch(self.root / 'tools' / 'helper.py', '# handwritten')
        _touch(self.root / 'tools' / 'tests' / 'test_helper.py', '# test')
        _touch(self.root / 'tools' / 'hooks' / 'utils.py', '# hook')
        self.assertEqual(_orphan_py(self.root), [])

    def test_skip_dirs_are_excluded(self) -> None:
        for skip in ('.git', '.github', '.ipynb_checkpoints', '__pycache__', '.venv', 'venv'):
            _touch(self.root / skip / 'noise.py', '# ignored')
        self.assertEqual(_orphan_py(self.root), [])

    def test_orphans_sorted_and_relative(self) -> None:
        """pathlib sorts by parts-tuples, not raw string: ('a','c.py') < ('a.py',)."""
        _touch(self.root / 'b.py')
        _touch(self.root / 'a' / 'c.py')
        _touch(self.root / 'a.py')
        self.assertEqual(
            _orphan_py(self.root),
            [Path('a/c.py'), Path('a.py'), Path('b.py')],
        )

    def test_mixed_tree(self) -> None:
        # Two valid pairs, one orphan in example/, one handwritten in tools/.
        _nb(self.root / 'Aroon.ipynb')
        _touch(self.root / 'Aroon.py', '# ok')
        _nb(self.root / 'lecture' / 'L1.ipynb')
        _touch(self.root / 'lecture' / 'L1.py', '# ok')
        _touch(self.root / 'example' / 'deleted.py', '# orphan')
        _touch(self.root / 'tools' / 'ipynb_to_py.py', '# handwritten')
        self.assertEqual(_orphan_py(self.root), [Path('example/deleted.py')])

    def test_ipynb_without_py_is_not_an_orphan(self) -> None:
        """Missing .py is reported separately by the main sync loop, not as orphan."""
        _nb(self.root / 'NoPy.ipynb')
        self.assertEqual(_orphan_py(self.root), [])


class PairsTests(unittest.TestCase):
    """Pin _pairs: notebook discovery + checkpoint filtering + sorting."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_empty_tree_returns_no_pairs(self) -> None:
        self.assertEqual(_pairs(self.root), [])

    def test_single_notebook_paired_with_py_suffix(self) -> None:
        nb = _nb(self.root / 'Foo.ipynb')
        self.assertEqual(_pairs(self.root), [(nb, nb.with_suffix('.py'))])

    def test_nested_notebook_paired(self) -> None:
        nb = _nb(self.root / 'lecture' / 'L1.ipynb')
        self.assertEqual(_pairs(self.root), [(nb, self.root / 'lecture' / 'L1.py')])

    def test_root_level_checkpoints_excluded(self) -> None:
        _nb(self.root / '.ipynb_checkpoints' / 'Foo-checkpoint.ipynb')
        self.assertEqual(_pairs(self.root), [])

    def test_nested_checkpoints_excluded(self) -> None:
        _nb(self.root / 'lecture' / '.ipynb_checkpoints' / 'L1-checkpoint.ipynb')
        self.assertEqual(_pairs(self.root), [])

    def test_py_existence_not_required_for_pairing(self) -> None:
        """The pair is derived from the .ipynb; a missing .py is reported by main()."""
        nb = _nb(self.root / 'Solo.ipynb')
        pairs = _pairs(self.root)
        self.assertEqual(len(pairs), 1)
        nb_got, py_got = pairs[0]
        self.assertEqual(nb_got, nb)
        self.assertFalse(py_got.exists())

    def test_multiple_notebooks_sorted(self) -> None:
        _nb(self.root / 'B.ipynb')
        _nb(self.root / 'a' / 'C.ipynb')
        _nb(self.root / 'A.ipynb')
        got = [nb for nb, _ in _pairs(self.root)]
        self.assertEqual(got, sorted(got))


class DiffPreviewTests(unittest.TestCase):
    """Pin _diff_preview: labels, content markers, and truncation."""

    def test_identical_inputs_produce_empty_diff(self) -> None:
        self.assertEqual(_diff_preview('same\n', 'same\n', Path('X.ipynb')), '')

    def test_diff_carries_from_and_to_labels(self) -> None:
        out = _diff_preview('new\n', 'old\n', Path('Foo.ipynb'))
        self.assertIn('Foo.ipynb (on disk)', out)
        self.assertIn('Foo.ipynb (expected from .ipynb)', out)

    def test_diff_shows_added_and_removed_lines(self) -> None:
        out = _diff_preview('expected\n', 'actual\n', Path('X.ipynb'))
        self.assertIn('-actual', out)
        self.assertIn('+expected', out)

    def test_long_diff_truncated_with_marker(self) -> None:
        actual = ''.join(f'a{i}\n' for i in range(50))
        expected = ''.join(f'b{i}\n' for i in range(50))
        out = _diff_preview(expected, actual, Path('X.ipynb'), max_lines=20)
        self.assertIn('more diff lines truncated', out)
        # Header (3 lines) + 20 capped body + 1 truncation note.
        self.assertLessEqual(len(out.splitlines()), 21)


class MainTests(unittest.TestCase):
    """End-to-end on main(argv), with stdout/stderr captured."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _run(self, *argv: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = main([str(self.root), *argv])
        return rc, out.getvalue(), err.getvalue()

    def test_empty_tree_returns_one(self) -> None:
        rc, _, stderr = self._run()
        self.assertEqual(rc, 1)
        self.assertIn('No .ipynb files', stderr)

    def test_all_in_sync_returns_zero(self) -> None:
        _synced_pair(self.root / 'A.ipynb')
        _synced_pair(self.root / 'sub' / 'B.ipynb')
        rc, stdout, _ = self._run('--quiet')
        self.assertEqual(rc, 0)
        self.assertRegex(stdout, r'In sync:\s+2')

    def test_missing_py_returns_two(self) -> None:
        _nb(self.root / 'Solo.ipynb')  # no .py sibling written
        rc, stdout, _ = self._run()
        self.assertEqual(rc, 2)
        self.assertIn('MISSING:', stdout)
        self.assertRegex(stdout, r'Missing \.py sibling:\s+1')

    def test_drift_returns_two_with_diff(self) -> None:
        nb, py = _synced_pair(self.root / 'Drift.ipynb')
        py.write_text(convert_to_str(nb) + 'extra = 1\n', encoding='utf-8')
        rc, stdout, _ = self._run()
        self.assertEqual(rc, 2)
        self.assertIn('DRIFT:', stdout)
        self.assertIn('(on disk)', stdout)  # diff body rendered

    def test_drift_no_diff_suppresses_diff_body(self) -> None:
        nb, py = _synced_pair(self.root / 'Drift.ipynb')
        py.write_text(convert_to_str(nb) + 'extra = 1\n', encoding='utf-8')
        rc, stdout, _ = self._run('--no-diff')
        self.assertEqual(rc, 2)
        self.assertIn('DRIFT:', stdout)
        self.assertNotIn('(on disk)', stdout)  # diff body withheld

    def test_orphan_py_returns_two(self) -> None:
        _synced_pair(self.root / 'Keep.ipynb')  # keeps _pairs non-empty
        _touch(self.root / 'example' / 'orphan.py', '# stale\n')
        rc, stdout, _ = self._run()
        self.assertEqual(rc, 2)
        self.assertIn('ORPHAN:', stdout)
        self.assertRegex(stdout, r'Orphan \.py \(no \.ipynb\):\s+1')

    def test_conversion_error_returns_two(self) -> None:
        """A malformed .ipynb with an existing .py hits the convert_to_str error path."""
        _touch(self.root / 'Bad.ipynb', '{ not valid json')
        _touch(self.root / 'Bad.py', '# anything\n')
        rc, stdout, _ = self._run()
        self.assertEqual(rc, 2)
        self.assertIn('ERROR:', stdout)
        self.assertRegex(stdout, r'Conversion errors:\s+1')

    def test_quiet_suppresses_per_file_lines(self) -> None:
        _nb(self.root / 'Solo.ipynb')  # missing .py
        rc, stdout, _ = self._run('--quiet')
        self.assertEqual(rc, 2)
        self.assertNotIn('MISSING:', stdout)
        self.assertRegex(stdout, r'Missing \.py sibling:\s+1')


if __name__ == '__main__':
    unittest.main(verbosity=2)
