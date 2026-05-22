"""Unit tests for tools/check_converted_py.py.

Stdlib-only unittest. Closes the testing trifecta with M8 (converter)
and M9 (sync checker) — this is the third tool and the only one without
coverage to date. Smoke tests against the real 77-notebook tree exist
in CI; this file pins the helper behavior so refactors get caught at
unit level.

Run:
    python3 tools/tests/test_check_converted_py.py
    # or
    python3 -m unittest tools.tests.test_check_converted_py
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from check_converted_py import (  # noqa: E402
    MAGIC_RE,
    _compile_check,
    _magic_check,
    _paired_py_files,
    main,
)


def _touch(path: Path, content: str = '') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _nb(path: Path) -> Path:
    nb = {'cells': [], 'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}
    return _touch(path, json.dumps(nb))


class MagicRegexTests(unittest.TestCase):
    """Pin the MAGIC_RE shape — sync checker shares the convention."""

    def test_bang_matches(self) -> None:
        self.assertIsNotNone(MAGIC_RE.match('!ls'))

    def test_percent_matches(self) -> None:
        self.assertIsNotNone(MAGIC_RE.match('%matplotlib inline'))

    def test_double_percent_matches(self) -> None:
        self.assertIsNotNone(MAGIC_RE.match('%%time'))

    def test_question_matches(self) -> None:
        self.assertIsNotNone(MAGIC_RE.match('?help'))

    def test_hash_bang_does_not_match(self) -> None:
        """Commented magics ('# !ls') must not trip the leak detector."""
        self.assertIsNone(MAGIC_RE.match('# !ls'))

    def test_plain_code_does_not_match(self) -> None:
        self.assertIsNone(MAGIC_RE.match('import os'))
        self.assertIsNone(MAGIC_RE.match(''))


class PairedPyFilesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_empty_tree_returns_no_pairs(self) -> None:
        self.assertEqual(_paired_py_files(self.root), [])

    def test_single_notebook_at_root(self) -> None:
        nb = _nb(self.root / 'Foo.ipynb')
        pairs = _paired_py_files(self.root)
        self.assertEqual(pairs, [(nb, nb.with_suffix('.py'))])

    def test_nested_notebook_paired_with_py(self) -> None:
        nb = _nb(self.root / 'lecture' / 'L1.ipynb')
        pairs = _paired_py_files(self.root)
        self.assertEqual(pairs, [(nb, self.root / 'lecture' / 'L1.py')])

    def test_ipynb_checkpoints_excluded(self) -> None:
        _nb(self.root / '.ipynb_checkpoints' / 'Foo-checkpoint.ipynb')
        self.assertEqual(_paired_py_files(self.root), [])

    def test_nested_ipynb_checkpoints_excluded(self) -> None:
        _nb(self.root / 'lecture' / '.ipynb_checkpoints' / 'L1-checkpoint.ipynb')
        self.assertEqual(_paired_py_files(self.root), [])

    def test_py_existence_not_required_for_pairing(self) -> None:
        """The pair is built from .ipynb alone; missing .py is reported by main()."""
        nb = _nb(self.root / 'Solo.ipynb')
        pairs = _paired_py_files(self.root)
        self.assertEqual(len(pairs), 1)
        nb_got, py_got = pairs[0]
        self.assertEqual(nb_got, nb)
        self.assertFalse(py_got.exists())

    def test_multiple_notebooks_all_paired(self) -> None:
        _nb(self.root / 'A.ipynb')
        _nb(self.root / 'b' / 'B.ipynb')
        _nb(self.root / 'c' / 'd' / 'C.ipynb')
        pairs = _paired_py_files(self.root)
        self.assertEqual(len(pairs), 3)
        suffixes = {p[1].suffix for p in pairs}
        self.assertEqual(suffixes, {'.py'})


class CompileCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_valid_python_returns_none(self) -> None:
        py = _touch(self.root / 'ok.py', 'x = 1\n')
        self.assertIsNone(_compile_check(py))

    def test_empty_file_returns_none(self) -> None:
        py = _touch(self.root / 'empty.py', '')
        self.assertIsNone(_compile_check(py))

    def test_comments_only_returns_none(self) -> None:
        py = _touch(self.root / 'comments.py', '# hello\n# world\n')
        self.assertIsNone(_compile_check(py))

    def test_syntax_error_returns_message(self) -> None:
        py = _touch(self.root / 'bad.py', 'def broken(:\n')
        err = _compile_check(py)
        self.assertIsNotNone(err)
        self.assertIsInstance(err, str)

    def test_leaked_magic_caught_as_syntax_error(self) -> None:
        """An un-commented ``!cmd`` is invalid Python — py_compile must reject it."""
        py = _touch(self.root / 'magic.py', '!ls\n')
        self.assertIsNotNone(_compile_check(py))

    def test_leaked_percent_magic_caught(self) -> None:
        py = _touch(self.root / 'pct.py', '%matplotlib inline\n')
        self.assertIsNotNone(_compile_check(py))


class MagicCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_clean_file_returns_empty(self) -> None:
        py = _touch(self.root / 'ok.py', 'import os\nx = 1\n')
        self.assertEqual(_magic_check(py), [])

    def test_commented_magic_returns_empty(self) -> None:
        """Properly commented-out magics ('# !ls') are clean."""
        py = _touch(self.root / 'clean.py', '# !ls\n# %matplotlib inline\n')
        self.assertEqual(_magic_check(py), [])

    def test_leaked_bang_caught_with_lineno(self) -> None:
        py = _touch(self.root / 'leak.py', 'import os\n!ls\n')
        hits = _magic_check(py)
        self.assertEqual(len(hits), 1)
        lineno, content = hits[0]
        self.assertEqual(lineno, 2)
        self.assertIn('!ls', content)

    def test_leaked_percent_and_question_marks(self) -> None:
        py = _touch(self.root / 'multi.py', '%magic\nimport os\n?help\n')
        hits = _magic_check(py)
        self.assertEqual([h[0] for h in hits], [1, 3])

    def test_indented_magic_caught_via_lstrip(self) -> None:
        """_magic_check lstrips before matching — pin this behavior."""
        py = _touch(self.root / 'indent.py', '    !ls\n')
        hits = _magic_check(py)
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0][0], 1)

    def test_line_truncated_to_120_chars(self) -> None:
        long_tail = 'x' * 200
        py = _touch(self.root / 'long.py', '!' + long_tail + '\n')
        hits = _magic_check(py)
        self.assertEqual(len(hits), 1)
        self.assertEqual(len(hits[0][1]), 120)


class MainTests(unittest.TestCase):
    """End-to-end on the helper-level main(), with stdout/stderr captured."""

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

    def test_all_pairs_clean_returns_zero(self) -> None:
        _nb(self.root / 'A.ipynb')
        _touch(self.root / 'A.py', '# ok\nimport os\n')
        _nb(self.root / 'sub' / 'B.ipynb')
        _touch(self.root / 'sub' / 'B.py', 'x = 1\n')
        rc, stdout, _ = self._run('--quiet')
        self.assertEqual(rc, 0)
        self.assertIn('OK:                  2', stdout)

    def test_missing_py_returns_two(self) -> None:
        _nb(self.root / 'Solo.ipynb')
        rc, stdout, _ = self._run()
        self.assertEqual(rc, 2)
        self.assertIn('MISSING:', stdout)

    def test_compile_failure_returns_two(self) -> None:
        _nb(self.root / 'Bad.ipynb')
        _touch(self.root / 'Bad.py', 'def broken(:\n')
        rc, stdout, _ = self._run()
        self.assertEqual(rc, 2)
        self.assertIn('COMPILE:', stdout)

    def test_magic_leak_returns_two(self) -> None:
        """A leaked magic surfaces as both a compile failure and a magic hit;
        either way rc must be 2."""
        _nb(self.root / 'Magic.ipynb')
        _touch(self.root / 'Magic.py', '!ls\n')
        rc, _, _ = self._run()
        self.assertEqual(rc, 2)

    def test_quiet_suppresses_per_file_lines(self) -> None:
        _nb(self.root / 'Solo.ipynb')  # missing .py
        rc, stdout, _ = self._run('--quiet')
        self.assertEqual(rc, 2)
        self.assertNotIn('MISSING:', stdout)
        self.assertIn('Missing .py sibling: 1', stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
