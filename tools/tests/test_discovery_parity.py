"""Cross-tool notebook-discovery parity guard (M25).

Three tools in the toolchain independently re-implement ".ipynb discovery
+ .ipynb_checkpoints filtering", each with its own copy of the walk:

  * ``ipynb_to_py.main`` root-walk  -- the converter's source of truth for
    *which* notebooks get a regenerated ``.py`` (line: ``base.rglob('*.ipynb')``
    filtered by ``'.ipynb_checkpoints' not in p.parts``)
  * ``check_ipynb_py_sync._pairs``  -- which notebooks the sync checker
    byte-for-byte compares against disk
  * ``check_converted_py._paired_py_files`` -- which generated ``.py`` the
    validator compiles + magic-leak scans

Nothing forced these three to enumerate the *same* set. If someone later
adds a skip dir (or tweaks the checkpoint filter) in one walk but not the
others, coverage silently diverges: a notebook could be converted yet never
sync-checked, or sync-checked yet never compile-validated -- a gap CI cannot
surface because each step only sees its own slice.

This is the same "only holds by convention" invariant that M9 (orphan),
M18 (CI parity), and M20-M24 (README/install parity) kept closing. M25
locks it as a *behavioral* parity test: run all three real discovery paths
on one shared fixture tree (root nb, nested nb, plus root-level and nested
``.ipynb_checkpoints/`` notebooks that must be excluded) and assert the
discovered notebook sets are identical. Pure stdlib; no production change.

M36 broadened the shared filter: the three walks now skip the full
``ipynb_to_py._SKIP_DIR_PARTS`` set (``.git``, ``.github``,
``.ipynb_checkpoints``, ``__pycache__``, ``.venv``, ``venv``) via the shared
``_in_skipped_dir`` predicate, not just ``.ipynb_checkpoints``. Before M36 a
notebook bundled under ``.venv/`` was discovered and spuriously converted by
all three walks, while ``_orphan_py`` already skipped it -- an asymmetry the
shared constant closes. ``SkipDirParityTests`` extends the behavioral parity
to every skip dir and pins the canonical set.

Run:
    python3 tools/tests/test_discovery_parity.py
    # or
    python3 -m unittest tools.tests.test_discovery_parity
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

import ipynb_to_py  # noqa: E402
from ipynb_to_py import _SKIP_DIR_PARTS  # noqa: E402
from check_converted_py import _paired_py_files  # noqa: E402
from check_ipynb_py_sync import _pairs  # noqa: E402
from check_ipynb_py_sync import _SKIP_DIR_PARTS as _SYNC_SKIP_DIR_PARTS  # noqa: E402
from check_converted_py import _in_skipped_dir as _VAL_IN_SKIPPED  # noqa: E402

# Matches the converter's --dry-run line: "[dry] <rel> -> <rel_py>".
_DRY_RE = re.compile(r'^\[dry\] (.+?) -> ')

# A minimal but valid notebook so convert_to_str() (run during --dry-run
# parseability validation, see M16) succeeds for every fixture file.
_MINIMAL_NB = json.dumps(
    {'cells': [], 'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}
)


def _write_nb(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_MINIMAL_NB, encoding='utf-8')


def _rel_posix(paths, root: Path) -> set[str]:
    """Normalize an iterable of notebook Paths to root-relative posix strings."""
    out = set()
    for p in paths:
        p = Path(p)
        try:
            p = p.relative_to(root)
        except ValueError:
            pass
        out.add(p.as_posix())
    return out


def _converter_discovers(root: Path) -> set[str]:
    """Notebooks the converter's root-walk actually visits.

    Exercised through the real production path: run ``main(['--dry-run', root])``
    and parse the ``[dry] <rel> -> ...`` lines. Avoids duplicating the walk
    logic in the test (which would defeat the parity guard's purpose).
    """
    buf = io.StringIO()
    with redirect_stdout(buf), redirect_stderr(io.StringIO()):
        ipynb_to_py.main(['--dry-run', str(root)])
    found = set()
    for line in buf.getvalue().splitlines():
        m = _DRY_RE.match(line)
        if m:
            found.add(Path(m.group(1)).as_posix())
    return found


def _pairs_discovers(root: Path) -> set[str]:
    return _rel_posix((nb for nb, _py in _pairs(root)), root)


def _validator_discovers(root: Path) -> set[str]:
    return _rel_posix((nb for nb, _py in _paired_py_files(root)), root)


class NotebookDiscoveryParityTests(unittest.TestCase):
    """All three discovery paths must enumerate the identical notebook set."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        # Three real notebooks the toolchain should process.
        _write_nb(self.root / 'A.ipynb')
        _write_nb(self.root / 'sub' / 'B.ipynb')
        _write_nb(self.root / 'sub' / 'deep' / 'C.ipynb')
        # Two checkpoint notebooks that every walk must skip:
        # one at root level (the M11 filter bug), one nested.
        _write_nb(self.root / '.ipynb_checkpoints' / 'A-checkpoint.ipynb')
        _write_nb(self.root / 'sub' / '.ipynb_checkpoints' / 'B-checkpoint.ipynb')
        self.expected = {'A.ipynb', 'sub/B.ipynb', 'sub/deep/C.ipynb'}

    def tearDown(self):
        self._tmp.cleanup()

    # --- each path matches the expected real-notebook set ---------------

    def test_converter_dryrun_discovers_expected(self):
        self.assertEqual(_converter_discovers(self.root), self.expected)

    def test_pairs_discovers_expected(self):
        self.assertEqual(_pairs_discovers(self.root), self.expected)

    def test_validator_discovers_expected(self):
        self.assertEqual(_validator_discovers(self.root), self.expected)

    # --- the core cross-tool parity assertion ---------------------------

    def test_all_three_discover_identical_set(self):
        conv = _converter_discovers(self.root)
        pairs = _pairs_discovers(self.root)
        val = _validator_discovers(self.root)
        self.assertEqual(conv, pairs, 'converter vs sync-checker discovery diverged')
        self.assertEqual(pairs, val, 'sync-checker vs validator discovery diverged')

    # --- checkpoint exclusion is shared by all three --------------------

    def test_root_level_checkpoint_excluded_by_all(self):
        ckpt = 'A-checkpoint.ipynb'
        for found in (
            _converter_discovers(self.root),
            _pairs_discovers(self.root),
            _validator_discovers(self.root),
        ):
            self.assertFalse(
                any(ckpt in f for f in found),
                f'root-level checkpoint leaked into discovery: {found}',
            )

    def test_nested_checkpoint_excluded_by_all(self):
        ckpt = 'B-checkpoint.ipynb'
        for found in (
            _converter_discovers(self.root),
            _pairs_discovers(self.root),
            _validator_discovers(self.root),
        ):
            self.assertFalse(
                any(ckpt in f for f in found),
                f'nested checkpoint leaked into discovery: {found}',
            )

    # --- negative control: the fixture actually exercises the filter ----

    def test_fixture_actually_contains_checkpoints(self):
        # Guard against a vacuous pass: if the fixture had no checkpoint
        # notebooks, the exclusion tests would pass trivially. A raw rglob
        # must see 5 .ipynb while every discovery path sees only 3.
        raw = {p.relative_to(self.root).as_posix() for p in self.root.rglob('*.ipynb')}
        self.assertEqual(len(raw), 5)
        self.assertEqual(len(self.expected), 3)
        self.assertEqual(_converter_discovers(self.root), self.expected)

    # --- empty tree: all three agree on "nothing" -----------------------

    def test_empty_tree_all_three_agree_empty(self):
        with tempfile.TemporaryDirectory() as empty:
            root = Path(empty).resolve()
            self.assertEqual(_converter_discovers(root), set())
            self.assertEqual(_pairs_discovers(root), set())
            self.assertEqual(_validator_discovers(root), set())


class SkipDirParityTests(unittest.TestCase):
    """All three discovery walks must skip the full _SKIP_DIR_PARTS set (M36).

    Before M36 each walk filtered only '.ipynb_checkpoints', so a notebook
    bundled under .venv/ (etc.) was discovered and spuriously converted while
    _orphan_py already skipped it. These tests lock the broadened filter as a
    behavioral parity: a notebook placed under every skip dir must be invisible
    to all three real discovery paths, and the three must still agree.
    """

    # The skip dirs that can realistically contain a stray .ipynb (a package
    # shipped under .venv, a stale checkpoint, etc.). All come from the one
    # shared constant; we assert against that constant, not a hard-coded copy.
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name).resolve()
        _write_nb(self.root / 'real.ipynb')
        _write_nb(self.root / 'pkg' / 'nested.ipynb')
        # One bundled notebook under each skip dir (root-level and nested).
        for sd in _SKIP_DIR_PARTS:
            _write_nb(self.root / sd / 'bundled.ipynb')
            _write_nb(self.root / 'pkg' / sd / 'deep_bundled.ipynb')
        self.expected = {'real.ipynb', 'pkg/nested.ipynb'}

    def tearDown(self):
        self._tmp.cleanup()

    def test_skip_dir_notebooks_excluded_by_all_three(self):
        self.assertEqual(_converter_discovers(self.root), self.expected)
        self.assertEqual(_pairs_discovers(self.root), self.expected)
        self.assertEqual(_validator_discovers(self.root), self.expected)

    def test_all_three_agree_with_skip_dirs_present(self):
        conv = _converter_discovers(self.root)
        pairs = _pairs_discovers(self.root)
        val = _validator_discovers(self.root)
        self.assertEqual(conv, pairs, 'converter vs sync-checker diverged on skip dirs')
        self.assertEqual(pairs, val, 'sync-checker vs validator diverged on skip dirs')

    def test_fixture_actually_contains_skip_dir_notebooks(self):
        # Negative control: raw rglob must see far more than the 2 real ones,
        # else the exclusion assertion above would pass vacuously.
        raw = {p.relative_to(self.root).as_posix() for p in self.root.rglob('*.ipynb')}
        # 2 real + 2 per skip dir.
        self.assertEqual(len(raw), 2 + 2 * len(_SKIP_DIR_PARTS))
        self.assertTrue(any('.venv/' in r for r in raw))

    def test_each_skip_dir_individually_excluded(self):
        # Pin each skip dir on its own so a future edit that drops one from the
        # set (e.g. removes '__pycache__') is caught, not masked by the others.
        for sd in _SKIP_DIR_PARTS:
            with self.subTest(skip_dir=sd):
                with tempfile.TemporaryDirectory() as d:
                    root = Path(d).resolve()
                    _write_nb(root / 'keep.ipynb')
                    _write_nb(root / sd / 'drop.ipynb')
                    self.assertEqual(_converter_discovers(root), {'keep.ipynb'})
                    self.assertEqual(_pairs_discovers(root), {'keep.ipynb'})
                    self.assertEqual(_validator_discovers(root), {'keep.ipynb'})


class SkipDirConstantParityTests(unittest.TestCase):
    """The skip-dir constant must be the single shared object across modules."""

    def test_sync_reuses_converter_constant(self):
        # check_ipynb_py_sync imports _SKIP_DIR_PARTS from the converter rather
        # than re-declaring it (M36 removed the 4th independent copy).
        self.assertIs(_SYNC_SKIP_DIR_PARTS, _SKIP_DIR_PARTS)

    def test_validator_reuses_converter_predicate(self):
        self.assertIs(_VAL_IN_SKIPPED, ipynb_to_py._in_skipped_dir)

    def test_canonical_skip_dir_set(self):
        # Pin the exact set so widening/narrowing the discovery surface is a
        # deliberate, reviewed change rather than a silent drift.
        self.assertEqual(
            set(_SKIP_DIR_PARTS),
            {'.git', '.github', '.ipynb_checkpoints', '__pycache__', '.venv', 'venv'},
        )

    def test_checkpoints_still_in_set(self):
        # The pre-M36 behavior (filter .ipynb_checkpoints) must remain a subset.
        self.assertIn('.ipynb_checkpoints', _SKIP_DIR_PARTS)


if __name__ == '__main__':
    unittest.main()
