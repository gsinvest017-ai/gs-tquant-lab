"""Behavior-parity guard: converter comment-out scan == validator leak scan.

M32 made both tools share the string scanner (ipynb_to_py._advance_string_state)
and M33 made them share the textual predicate (ipynb_to_py._is_magic_line). But
the *string-aware scanning loop* that combines those two pieces — "track the
triple-quoted-string state across physical lines, and apply the predicate only
at top level (state is None)" — is still written **twice, independently**:

  - converter  ipynb_to_py._sanitize_code        decides which lines to comment
  - validator  check_converted_py._magic_check    decides which lines leaked

Nothing forces the two loops to flag the *same* lines on the same input. A
refactor of either loop's gating (e.g. computing `in_string` after advancing
state instead of before, or relaxing the `state is None` guard) would silently
desync them — and CI can't catch it, because in production the two tools never
see the same raw text (converter & sync checker share _sanitize_code; the
validator only ever scans the already-converted .py, where magics are already
commented). This file closes that gap the M25 way — *behavioral* parity rather
than text parsing: it runs both real scan loops on the same raw code text and
asserts they enumerate exactly the same set of magic line numbers.

Stdlib-only unittest.

Run:
    python3 tools/tests/test_magic_scan_parity.py
    # or
    python3 -m unittest tools.tests.test_magic_scan_parity
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import ipynb_to_py  # noqa: E402
from check_converted_py import _magic_check  # noqa: E402

TQ = "'''"  # single-quote triple delimiter, kept out of this module's docstring
DQ = '"""'


def _converter_commented(text: str) -> set[int]:
    """1-based line numbers the converter's _sanitize_code comments out.

    The converter only ever transforms a magic line by prefixing '# '; every
    other line is emitted verbatim. So a line differs between input and output
    iff the converter decided it was a magic to comment. We assert that '# '
    shape too, so this helper can never silently mis-attribute some *other*
    transform as a comment-out.
    """
    raw = text.splitlines()
    out = ipynb_to_py._sanitize_code(text).splitlines()
    assert len(raw) == len(out), (
        f'_sanitize_code changed the line count ({len(raw)} -> {len(out)}); '
        'the parity helper assumes a 1:1 line mapping'
    )
    commented: set[int] = set()
    for i, (before, after) in enumerate(zip(raw, out), 1):
        if before != after:
            assert after == '# ' + before, (
                f'converter applied a non-comment transform on line {i}: '
                f'{before!r} -> {after!r}'
            )
            commented.add(i)
    return commented


class MagicScanParityTests(unittest.TestCase):
    """For arbitrary raw code text, the converter's comment-out decisions and
    the validator's leak-detection must agree line-for-line."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _validator_flagged(self, text: str) -> set[int]:
        """1-based line numbers _magic_check flags when run on raw text.

        _magic_check normally scans the already-converted .py (so it finds 0
        leaks); here we deliberately feed it the *uncommented* source so its
        scan loop has to identify the same magics the converter would comment.
        """
        probe = self.tmp / 'probe.py'
        probe.write_text(text, encoding='utf-8')
        return {lineno for lineno, _ in _magic_check(probe)}

    def _assert_parity(self, text: str, expected: set[int]) -> None:
        commented = _converter_commented(text)
        flagged = self._validator_flagged(text)
        self.assertEqual(
            commented, flagged,
            f'scan loops disagree: converter commented {sorted(commented)} '
            f'but validator flagged {sorted(flagged)}',
        )
        # Pin the expected set too, so a *shared* bug that desyncs both tools
        # in the same direction (still equal to each other) is still caught.
        self.assertEqual(commented, expected)

    # --- no magic -------------------------------------------------------
    def test_plain_code_flags_nothing(self):
        self._assert_parity('import os\nx = 1\n', set())

    def test_trailing_question_comment_is_not_magic(self):
        # M28 regression: a legit line ending in '?' must NOT be commented.
        self._assert_parity('x = run()  # done?\n', set())

    # --- leading magics -------------------------------------------------
    def test_leading_bang(self):
        self._assert_parity('!ls -la\n', {1})

    def test_leading_percent(self):
        self._assert_parity('%matplotlib inline\nx = 1\n', {1})

    def test_cell_magic(self):
        self._assert_parity('%%time\nx = 1\n', {1})

    def test_prefix_help(self):
        self._assert_parity('?str\n', {1})

    def test_indented_magic(self):
        # lstrip() in both loops means indentation does not hide a magic.
        self._assert_parity('    %time foo\n', {1})

    # --- suffix help (the M33 capability both tools must share) ---------
    def test_suffix_help(self):
        self._assert_parity('df.head?\n', {1})

    def test_double_suffix_help(self):
        self._assert_parity('obj??\n', {1})

    # --- string-awareness (the M31/M32 fixes both loops must honor) -----
    def test_magic_chars_inside_docstring_are_not_flagged(self):
        text = DQ + '\n!run this\n%(name)s\ndf.head?\n' + DQ + '\nx = 1\n'
        self._assert_parity(text, set())

    def test_magic_after_closing_triple_string(self):
        text = DQ + '\ndoc\n' + DQ + '\n!ls\n'
        self._assert_parity(text, {4})

    def test_magic_before_opening_triple_string(self):
        text = '!ls\n' + DQ + '\ndoc\n' + DQ + '\n'
        self._assert_parity(text, {1})

    def test_single_quote_triple_string(self):
        text = TQ + '\n!inside\n' + TQ + '\n'
        self._assert_parity(text, set())

    def test_inline_open_close_then_magic(self):
        # A triple string that opens and closes on one line leaves state=None,
        # so the next line is scanned at top level.
        text = 's = ' + DQ + 'ab' + DQ + '\n!ls\n'
        self._assert_parity(text, {2})

    # --- the combined torture case --------------------------------------
    def test_mixed_document(self):
        text = (
            '%matplotlib inline\n'   # 1 magic
            'import os\n'            # 2 code
            + DQ + '\n'              # 3 opens triple string
            '!inside\n'              # 4 in-string, NOT magic
            + DQ + '\n'              # 5 closes
            'df.head?\n'             # 6 suffix help, magic
            'x = 1  # really?\n'     # 7 trailing-? comment, NOT magic
        )
        self._assert_parity(text, {1, 6})

    # --- helper invariant -----------------------------------------------
    def test_converter_only_ever_prefixes_hash_space(self):
        # The whole parity argument rests on _sanitize_code transforming magic
        # lines by exactly '# ' and nothing else; lock that here so the helper
        # assertion above is itself meaningful.
        text = '!ls\nimport os\n%time\n'
        out = ipynb_to_py._sanitize_code(text).splitlines()
        self.assertEqual(out[0], '# !ls')
        self.assertEqual(out[1], 'import os')
        self.assertEqual(out[2], '# %time')


if __name__ == '__main__':
    unittest.main()
