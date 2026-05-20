"""Unit tests for tools/ipynb_to_py.py.

Stdlib-only unittest, no pytest dependency. Tests cover the pure-function
core (_comment_block, _sanitize_code, convert_to_str) so regressions in
cell-type handling, magic sanitization, or HEADER/CELL_SEP formatting are
caught before they corrupt the 77 generated .py siblings.

Run:
    python3 tools/tests/test_ipynb_to_py.py
    # or
    python3 -m unittest tools.tests.test_ipynb_to_py
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

from ipynb_to_py import (  # noqa: E402
    CELL_SEP,
    HEADER,
    _comment_block,
    _sanitize_code,
    convert_to_str,
)


def _cell(kind: str, source):
    return {'cell_type': kind, 'source': source, 'metadata': {}}


def _write_nb(cells, tmpdir: Path) -> Path:
    nb = {
        'cells': cells,
        'metadata': {},
        'nbformat': 4,
        'nbformat_minor': 5,
    }
    path = tmpdir / 'fixture.ipynb'
    path.write_text(json.dumps(nb), encoding='utf-8')
    return path


class CommentBlockTests(unittest.TestCase):
    def test_single_line(self):
        self.assertEqual(_comment_block('hello'), '# hello\n')

    def test_multi_line(self):
        self.assertEqual(_comment_block('a\nb'), '# a\n# b\n')

    def test_blank_line_becomes_bare_hash(self):
        # Empty lines should NOT have a trailing space after #, just '#'
        # (preserves "lines stripped to empty stay visually empty")
        self.assertEqual(_comment_block('a\n\nb'), '# a\n#\n# b\n')

    def test_empty_string_yields_bare_hash(self):
        # splitlines('') returns []; `or ['']` fallback gives one '#' line
        self.assertEqual(_comment_block(''), '#\n')


class SanitizeCodeTests(unittest.TestCase):
    def test_plain_code_lines_preserved_verbatim(self):
        # Note: trailing newline handling is asymmetric — see
        # test_trailing_newline_stripped_when_present below.
        src = 'import os\nx = 1'
        self.assertEqual(_sanitize_code(src), 'import os\nx = 1\n')

    def test_shell_magic_commented(self):
        self.assertEqual(_sanitize_code('!pip install foo'), '# !pip install foo\n')

    def test_line_magic_commented(self):
        self.assertEqual(_sanitize_code('%matplotlib inline'), '# %matplotlib inline\n')

    def test_cell_magic_commented(self):
        self.assertEqual(
            _sanitize_code('%%bash\nls -la'),
            '# %%bash\nls -la\n',
        )

    def test_question_prefix_commented(self):
        self.assertEqual(_sanitize_code('?help'), '# ?help\n')

    def test_question_suffix_commented(self):
        self.assertEqual(_sanitize_code('help?'), '# help?\n')

    def test_double_question_suffix_commented(self):
        self.assertEqual(_sanitize_code('obj??'), '# obj??\n')

    def test_indented_magic_commented(self):
        # _sanitize_code uses lstrip() to detect magics even after whitespace
        self.assertEqual(_sanitize_code('    !echo hi'), '#     !echo hi\n')

    def test_mixed_magic_and_code(self):
        src = '!pip install foo\nimport foo\nfoo.do()'
        self.assertEqual(
            _sanitize_code(src),
            '# !pip install foo\nimport foo\nfoo.do()\n',
        )

    def test_trailing_newline_added_when_missing(self):
        # No trailing \n on input -> one added to output.
        self.assertEqual(_sanitize_code('x = 1'), 'x = 1\n')

    def test_trailing_newline_stripped_when_present(self):
        # ASYMMETRIC QUIRK (locked in by 77 generated .py siblings):
        # Input WITH a single trailing \n -> output has NO trailing \n,
        # because splitlines() drops it and the
        # `'\n' if not text.endswith('\n') else ''` branch then adds nothing.
        # convert_to_str compensates by prefixing every CELL_SEP with '\n',
        # so cell boundaries still render cleanly. Changing this asymmetry
        # would force a regeneration of all 77 .py siblings.
        self.assertEqual(_sanitize_code('x = 1\n'), 'x = 1')

    def test_double_trailing_newline_reduced_to_one(self):
        # 'x\n\n' has trailing \n, so splitlines -> ['x', ''], join -> 'x\n',
        # branch adds nothing -> 'x\n'.
        self.assertEqual(_sanitize_code('x = 1\n\n'), 'x = 1\n')


class ConvertToStrTests(unittest.TestCase):
    def setUp(self):
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self._tmp_ctx.name)

    def tearDown(self):
        self._tmp_ctx.cleanup()

    def _convert(self, cells) -> str:
        return convert_to_str(_write_nb(cells, self.tmpdir))

    def test_empty_notebook_emits_only_header(self):
        out = self._convert([])
        self.assertEqual(out, HEADER.format(src='fixture.ipynb'))
        self.assertNotIn('# %%', out)

    def test_header_contains_source_filename(self):
        out = self._convert([_cell('code', 'x = 1')])
        self.assertTrue(out.startswith('# -*- coding: utf-8 -*-\n'))
        self.assertIn('Auto-generated from fixture.ipynb', out)

    def test_code_cell_body_preserved(self):
        out = self._convert([_cell('code', 'import os\nprint(os.getcwd())')])
        self.assertIn('import os', out)
        self.assertIn('print(os.getcwd())', out)

    def test_code_cell_magic_commented_in_output(self):
        out = self._convert([_cell('code', '!pip install foo\nimport foo')])
        self.assertIn('# !pip install foo', out)
        self.assertIn('import foo', out)
        self.assertNotIn('\n!pip install', out)

    def test_markdown_cell_becomes_comment_block(self):
        out = self._convert([_cell('markdown', '# Section\nHello world')])
        self.assertIn('# # Section', out)
        self.assertIn('# Hello world', out)

    def test_raw_cell_becomes_comment_block(self):
        out = self._convert([_cell('raw', 'raw content\nline 2')])
        self.assertIn('# raw content', out)
        self.assertIn('# line 2', out)

    def test_empty_source_cell_skipped_but_index_preserved(self):
        out = self._convert([_cell('code', ''), _cell('code', 'x = 1')])
        self.assertNotIn(CELL_SEP.format(kind='code', idx=0), out)
        self.assertIn(CELL_SEP.format(kind='code', idx=1), out)
        self.assertIn('x = 1', out)

    def test_whitespace_only_source_cell_skipped(self):
        out = self._convert([_cell('code', '   \n\t\n'), _cell('code', 'x = 1')])
        self.assertNotIn('cell 0', out)
        self.assertIn('cell 1', out)

    def test_source_as_list_joined(self):
        # nbformat stores source as either str or list-of-str (line-by-line)
        out = self._convert([_cell('code', ['import os\n', 'x = 1\n'])])
        self.assertIn('import os', out)
        self.assertIn('x = 1', out)

    def test_cell_marker_kind_and_index(self):
        out = self._convert([
            _cell('markdown', 'header'),
            _cell('code', 'x = 1'),
        ])
        self.assertIn('# %% [markdown] cell 0', out)
        self.assertIn('# %% [code] cell 1', out)

    def test_unknown_cell_type_falls_through_to_comment(self):
        # Anything that isn't 'code' is emitted as a comment block
        out = self._convert([_cell('weird', 'mystery content')])
        self.assertIn('# %% [weird] cell 0', out)
        self.assertIn('# mystery content', out)

    def test_cell_order_preserved(self):
        out = self._convert([
            _cell('code', 'A = 1'),
            _cell('markdown', 'middle text'),
            _cell('code', 'B = 2'),
        ])
        self.assertLess(out.index('A = 1'), out.index('middle text'))
        self.assertLess(out.index('middle text'), out.index('B = 2'))

    def test_missing_cell_type_defaults_to_unknown(self):
        # Defensive: cells without cell_type still produce something usable
        out = convert_to_str(_write_nb([{'source': 'foo', 'metadata': {}}], self.tmpdir))
        self.assertIn('# %% [unknown] cell 0', out)
        self.assertIn('# foo', out)

    def test_missing_source_defaults_to_empty_and_skipped(self):
        # A cell with no 'source' key at all is treated as empty -> skipped
        out = convert_to_str(_write_nb([
            {'cell_type': 'code', 'metadata': {}},
            _cell('code', 'x = 1'),
        ], self.tmpdir))
        self.assertNotIn('cell 0', out)
        self.assertIn('cell 1', out)

    def test_idempotent_for_same_input(self):
        cells = [_cell('code', 'x = 1\n'), _cell('markdown', 'note')]
        a = self._convert(cells)
        b = self._convert(cells)
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main()
