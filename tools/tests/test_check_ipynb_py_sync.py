"""Unit tests for tools/check_ipynb_py_sync.py.

Stdlib-only unittest. Focuses on the orphan-detection logic added in M9
(`_orphan_py`), which is the only piece in the checker without coverage
elsewhere — the in-sync / drift / missing paths are exercised end-to-end
in CI against the real 77 notebook pairs.

Run:
    python3 tools/tests/test_check_ipynb_py_sync.py
    # or
    python3 -m unittest tools.tests.test_check_ipynb_py_sync
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from check_ipynb_py_sync import _orphan_py  # noqa: E402


def _touch(path: Path, content: str = '') -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return path


def _nb(path: Path) -> Path:
    nb = {'cells': [], 'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}
    return _touch(path, json.dumps(nb))


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


if __name__ == '__main__':
    unittest.main(verbosity=2)
