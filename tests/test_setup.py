"""ファイル競合とZIPパス脱出、共有設定への影響を検査する。"""
import importlib
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
setup = importlib.import_module('setup')
from aivep import environment


class IsolationTests(unittest.TestCase):
    def test_environment_keeps_codex_auth_and_isolates_product(self):
        with patch.dict(os.environ, {'HOME': '/original', 'CODEX_HOME': '/auth', 'PYTHONPATH': '/shared'}):
            env = environment(Path('/project'))
        self.assertEqual(env['CODEX_HOME'], '/auth')
        self.assertEqual(env['HOME'], '/project')
        self.assertEqual(env['AIVEP_DATA_DIR'], '/project/.ai-video-edit-pro/data')
        self.assertNotIn('PYTHONPATH', env)
        self.assertEqual(os.environ.get('HOME'), str(Path.home()))

    def test_existing_skill_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(setup, 'ROOT', Path(directory)):
            skill = Path(directory) / '.agents/skills/ai-video-edit'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('既存スキル')
            with self.assertRaisesRegex(ValueError, '競合'):
                setup.check_conflicts()
            self.assertEqual((skill / 'SKILL.md').read_text(), '既存スキル')

    def test_existing_hook_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(setup, 'ROOT', Path(directory)):
            hook = Path(directory) / '.codex/hooks.json'
            hook.parent.mkdir()
            hook.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'hook'):
                setup.check_conflicts()
            self.assertEqual(hook.read_text(), '{}')

    def test_directory_symlink_cannot_redirect_installation(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(setup, 'ROOT', Path(directory)):
            outside = Path(directory) / 'shared'
            outside.mkdir()
            (Path(directory) / '.local').symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'ディレクトリ'):
                setup.check_conflicts()
            self.assertEqual(list(outside.iterdir()), [])

    def test_zip_rejects_traversal_and_symlink_before_extraction(self):
        for bad_name, mode in [('ai-video-edit-pro-v2.5.15/../../outside', 0),
                               ('ai-video-edit-pro-v2.5.15/link', stat.S_IFLNK | 0o777),
                               ('/absolute', 0)]:
            with self.subTest(name=bad_name), tempfile.TemporaryDirectory() as directory:
                archive = Path(directory) / 'package.zip'
                out = Path(directory) / 'out'
                with zipfile.ZipFile(archive, 'w') as stream:
                    stream.writestr('ai-video-edit-pro-v2.5.15/VERSION', '2.5.15')
                    info = zipfile.ZipInfo(bad_name)
                    info.external_attr = mode << 16
                    stream.writestr(info, 'outside')
                with self.assertRaises(ValueError):
                    setup.extract_safe(archive, out)
                self.assertFalse(out.exists())

    def test_valid_zip_extracts(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'package.zip'
            out = Path(directory) / 'out'
            with zipfile.ZipFile(archive, 'w') as stream:
                stream.writestr('ai-video-edit-pro-v2.5.15/VERSION', '2.5.15')
            setup.extract_safe(archive, out)
            self.assertEqual((out / 'ai-video-edit-pro-v2.5.15/VERSION').read_text(), '2.5.15')


if __name__ == '__main__':
    unittest.main()
