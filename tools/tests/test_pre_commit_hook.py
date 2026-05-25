"""Integration tests for tools/hooks/pre-commit and tools/hooks/install.sh.

Stdlib-only unittest + subprocess. Each test runs in an isolated temp git
repo with the hook installed the same way `install.sh` arranges it (a
symlink from .git/hooks/pre-commit -> ../../tools/hooks/pre-commit). The
hook script and the converter are copied in fresh per test, so tests
cannot leak state between runs.

Run:
    python3 tools/tests/test_pre_commit_hook.py
    # or
    python3 -m unittest tools.tests.test_pre_commit_hook
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
HOOK_SRC = TOOLS / 'hooks' / 'pre-commit'
INSTALL_SH = TOOLS / 'hooks' / 'install.sh'
CONVERTER = TOOLS / 'ipynb_to_py.py'


def _mini_nb(code: str = 'x = 1') -> str:
    return json.dumps({
        'cells': [
            {'cell_type': 'code', 'source': [code]},
        ],
        'metadata': {},
        'nbformat': 4,
        'nbformat_minor': 5,
    })


def _run(cmd, cwd, check=True):
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        check=check,
        capture_output=True,
        text=True,
    )


class _RepoFixture(unittest.TestCase):
    """Bootstraps an isolated git repo with the hook installed as a symlink."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self._init_repo()
        self._copy_tooling()
        self._install_hook_symlink()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _init_repo(self) -> None:
        _run(['git', 'init', '-q'], self.repo)
        _run(['git', 'config', 'user.email', 'test@example.invalid'], self.repo)
        _run(['git', 'config', 'user.name', 'Tester'], self.repo)
        _run(['git', 'config', 'commit.gpgsign', 'false'], self.repo)

    def _copy_tooling(self) -> None:
        (self.repo / 'tools' / 'hooks').mkdir(parents=True)
        shutil.copy(HOOK_SRC, self.repo / 'tools' / 'hooks' / 'pre-commit')
        shutil.copy(INSTALL_SH, self.repo / 'tools' / 'hooks' / 'install.sh')
        shutil.copy(CONVERTER, self.repo / 'tools' / 'ipynb_to_py.py')
        os.chmod(self.repo / 'tools' / 'hooks' / 'pre-commit', 0o755)
        os.chmod(self.repo / 'tools' / 'hooks' / 'install.sh', 0o755)

    def _install_hook_symlink(self) -> None:
        dst = self.repo / '.git' / 'hooks' / 'pre-commit'
        if dst.is_symlink() or dst.exists():
            dst.unlink()
        os.symlink('../../tools/hooks/pre-commit', dst)

    def _bootstrap(self) -> None:
        _run(['git', 'add', 'tools/'], self.repo)
        _run(['git', 'commit', '-q', '-m', 'bootstrap'], self.repo)

    def _stage(self, *paths: str) -> None:
        _run(['git', 'add', '--'] + list(paths), self.repo)

    def _commit(self, msg: str = 'change'):
        return _run(['git', 'commit', '-q', '-m', msg], self.repo, check=False)

    def _head_files(self):
        out = _run(['git', 'show', '--name-only', '--format=', 'HEAD'], self.repo).stdout
        return out.split()


class HookBehaviourTests(_RepoFixture):
    def test_no_staged_ipynb_is_passthrough(self) -> None:
        """Commit with no .ipynb staged: hook exits 0 and produces no .py outside tools/."""
        self._stage('tools/')
        r = self._commit('init')
        self.assertEqual(r.returncode, 0, r.stderr)
        outside = [
            p for p in self.repo.rglob('*.py')
            if 'tools' not in p.relative_to(self.repo).parts
        ]
        self.assertEqual(outside, [])

    def test_new_ipynb_regenerates_py_and_includes_in_commit(self) -> None:
        self._bootstrap()
        nb = self.repo / 'demo.ipynb'
        nb.write_text(_mini_nb("print('hello')"))
        self._stage('demo.ipynb')
        r = self._commit('add nb')
        self.assertEqual(r.returncode, 0, r.stderr)
        py = self.repo / 'demo.py'
        self.assertTrue(py.exists(), 'hook should have generated demo.py')
        self.assertIn("print('hello')", py.read_text())
        self.assertIn('demo.py', self._head_files())

    def test_modified_ipynb_regenerates_py_with_new_content(self) -> None:
        self._bootstrap()
        nb = self.repo / 'demo.ipynb'
        nb.write_text(_mini_nb('a = 1'))
        self._stage('demo.ipynb')
        self._commit('initial nb')
        nb.write_text(_mini_nb('a = 2'))
        self._stage('demo.ipynb')
        r = self._commit('update nb')
        self.assertEqual(r.returncode, 0, r.stderr)
        py_text = (self.repo / 'demo.py').read_text()
        self.assertIn('a = 2', py_text)
        self.assertNotIn('a = 1', py_text)
        self.assertIn('demo.py', self._head_files())

    def test_deleted_ipynb_also_removes_py_sibling(self) -> None:
        """When the user only stages the .ipynb deletion, hook should auto-remove the .py too."""
        self._bootstrap()
        nb = self.repo / 'demo.ipynb'
        nb.write_text(_mini_nb())
        self._stage('demo.ipynb')
        self._commit('add nb')
        py = self.repo / 'demo.py'
        self.assertTrue(py.exists(), 'precondition: hook should have generated demo.py')
        nb.unlink()
        # Stage only the .ipynb deletion; the hook must clean up demo.py.
        self._stage('demo.ipynb')
        r = self._commit('delete nb')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(py.exists(), 'hook should auto-remove .py when .ipynb is deleted')

    def test_deleted_ipynb_without_existing_py_is_silent(self) -> None:
        """If the .py sibling was never tracked, deletion of the .ipynb must not error."""
        self._bootstrap()
        nb = self.repo / 'orphan.ipynb'
        nb.write_text(_mini_nb())
        # Stage + commit the ipynb without ever generating a .py: use git add
        # --intent-to-add then commit just the ipynb after deleting any .py.
        self._stage('orphan.ipynb')
        self._commit('add nb')
        py = self.repo / 'orphan.py'
        if py.exists():
            _run(['git', 'rm', '-q', '--', 'orphan.py'], self.repo)
            self._commit('drop py')
        self.assertFalse(py.exists())
        nb.unlink()
        self._stage('orphan.ipynb')
        r = self._commit('delete nb')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(nb.exists())
        self.assertFalse(py.exists())

    def test_ipynb_checkpoints_directory_is_filtered(self) -> None:
        """Files under .ipynb_checkpoints/ must be skipped."""
        self._bootstrap()
        ckpt = self.repo / '.ipynb_checkpoints' / 'demo-checkpoint.ipynb'
        ckpt.parent.mkdir()
        ckpt.write_text(_mini_nb())
        self._stage('.ipynb_checkpoints/demo-checkpoint.ipynb')
        r = self._commit('add checkpoint')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(
            (self.repo / '.ipynb_checkpoints' / 'demo-checkpoint.py').exists(),
            'hook must not generate .py for files inside .ipynb_checkpoints/',
        )

    def test_multiple_ipynb_all_get_py_siblings(self) -> None:
        self._bootstrap()
        names = ['a.ipynb', 'sub/b.ipynb', 'c.ipynb']
        for name in names:
            p = self.repo / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(_mini_nb(f"# {name}"))
        self._stage(*names)
        r = self._commit('add three')
        self.assertEqual(r.returncode, 0, r.stderr)
        for name in names:
            py = self.repo / name.replace('.ipynb', '.py')
            self.assertTrue(py.exists(), f'missing generated sibling: {py}')
        head = self._head_files()
        self.assertIn('a.py', head)
        self.assertIn('sub/b.py', head)
        self.assertIn('c.py', head)

    def test_renamed_ipynb_generates_py_at_new_name(self) -> None:
        """git mv old.ipynb new.ipynb: hook regenerates new.py."""
        self._bootstrap()
        (self.repo / 'old.ipynb').write_text(_mini_nb('renamed = True'))
        self._stage('old.ipynb')
        self._commit('add old')
        _run(['git', 'mv', 'old.ipynb', 'new.ipynb'], self.repo)
        r = self._commit('rename')
        self.assertEqual(r.returncode, 0, r.stderr)
        new_py = self.repo / 'new.py'
        self.assertTrue(new_py.exists())
        self.assertIn('renamed = True', new_py.read_text())

    def test_rename_cleans_up_old_py(self) -> None:
        """git mv old.ipynb new.ipynb: hook regenerates new.py AND removes old.py."""
        self._bootstrap()
        (self.repo / 'old.ipynb').write_text(_mini_nb())
        self._stage('old.ipynb')
        self._commit('add old')
        self.assertTrue((self.repo / 'old.py').exists(), 'precondition: old.py exists')
        _run(['git', 'mv', 'old.ipynb', 'new.ipynb'], self.repo)
        r = self._commit('rename')
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((self.repo / 'old.py').exists(), 'old.py should be auto-removed')
        self.assertTrue((self.repo / 'new.py').exists(), 'new.py should be auto-generated')

    def test_py_contains_converter_header_and_cell_marker(self) -> None:
        """End-to-end sanity: the .py uses the converter's HEADER + CELL_SEP."""
        self._bootstrap()
        (self.repo / 'demo.ipynb').write_text(_mini_nb('value = 42'))
        self._stage('demo.ipynb')
        self._commit('add demo')
        text = (self.repo / 'demo.py').read_text()
        self.assertIn('Auto-generated from demo.ipynb', text)
        self.assertIn('# %% [code] cell 0', text)
        self.assertIn('value = 42', text)


class InstallShTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        _run(['git', 'init', '-q'], self.repo)
        (self.repo / 'tools' / 'hooks').mkdir(parents=True)
        shutil.copy(HOOK_SRC, self.repo / 'tools' / 'hooks' / 'pre-commit')
        shutil.copy(INSTALL_SH, self.repo / 'tools' / 'hooks' / 'install.sh')
        os.chmod(self.repo / 'tools' / 'hooks' / 'pre-commit', 0o755)
        os.chmod(self.repo / 'tools' / 'hooks' / 'install.sh', 0o755)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _install(self):
        return _run(['./tools/hooks/install.sh'], self.repo)

    def test_fresh_install_creates_symlink_to_relative_target(self) -> None:
        r = self._install()
        self.assertEqual(r.returncode, 0, r.stderr)
        dst = self.repo / '.git' / 'hooks' / 'pre-commit'
        self.assertTrue(dst.is_symlink(), f'expected symlink at {dst}')
        self.assertEqual(os.readlink(dst), '../../tools/hooks/pre-commit')

    def test_install_is_idempotent(self) -> None:
        self._install()
        r = self._install()
        self.assertEqual(r.returncode, 0, r.stderr)
        dst = self.repo / '.git' / 'hooks' / 'pre-commit'
        self.assertTrue(dst.is_symlink())
        backups = list((self.repo / '.git' / 'hooks').glob('pre-commit.backup.*'))
        self.assertEqual(backups, [], 'idempotent re-install should not produce backups')

    def test_existing_non_symlink_is_backed_up(self) -> None:
        dst = self.repo / '.git' / 'hooks' / 'pre-commit'
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text('#!/bin/sh\necho old\n')
        os.chmod(dst, 0o755)
        r = self._install()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(dst.is_symlink())
        backups = list((self.repo / '.git' / 'hooks').glob('pre-commit.backup.*'))
        self.assertEqual(len(backups), 1, f'expected exactly one backup, got {backups}')
        self.assertIn('echo old', backups[0].read_text())


if __name__ == '__main__':
    unittest.main(verbosity=2)
