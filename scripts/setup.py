#!/usr/bin/env python3
"""公式ZIPを検証し、共通ホスト設定を変更せずにCodex用の環境を導入する。"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

from aivep import ROOT, environment

VERSION = '2.5.15'
FILENAME = f'ai-video-edit-pro-v{VERSION}.zip'
URL = f'https://pro.coach-naoki.com/ai-video-edit-pro/releases/{VERSION}/{FILENAME}'
NAMES = ('ai-video-edit', 'telop-astra', 'video-analyse', 'taidan-edit')


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise ValueError('配布元のリダイレクトを拒否しました。')


def verified_zip(path):
    with urllib.request.build_opener(NoRedirect()).open(URL + '.sha256', timeout=30) as response:
        text = response.read(1024).decode().strip()
    match = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?' + re.escape(FILENAME), text)
    if not match:
        raise ValueError('公式SHA-256の形式が不正です。')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != match[1].lower():
        raise ValueError('配布ZIPのSHA-256が公式値と一致しません。')
    return digest


def extract_safe(path, destination):
    with zipfile.ZipFile(path) as archive:
        seen = set()
        for item in archive.infolist():
            name = item.filename.rstrip('/')
            parts = PurePosixPath(name).parts
            mode = item.external_attr >> 16
            if (not parts or parts[0] != f'ai-video-edit-pro-v{VERSION}'
                    or name.startswith('/') or '..' in parts or '\\' in name or ':' in name
                    or stat.S_ISLNK(mode) or name.casefold() in seen):
                raise ValueError('安全でないZIPエントリー: ' + name)
            seen.add(name.casefold())
        archive.extractall(destination)


def check_conflicts():
    for relative in ('.local', '.ai-video-edit-pro', '.agents', '.agents/skills', '.codex', '.codex/skills'):
        path = ROOT / relative
        if path.is_symlink() or (path.exists() and not path.is_dir()):
            raise ValueError('専用配置先が通常のディレクトリではありません: ' + str(path))
    installed = ROOT / '.ai-video-edit-pro/source.json'
    if installed.is_file():
        record = json.loads(installed.read_text())
        if (record.get('skills') != str(ROOT / '.ai-video-edit-pro/skills')
                or record.get('python') != str(ROOT / '.local/venv/bin/python')):
            raise ValueError('別環境の製品登録があります。既存環境を保持して停止します。')
    for area in ('.agents/skills', '.codex/skills'):
        for name in NAMES:
            target = ROOT / area / name
            expected = ROOT / '.ai-video-edit-pro/skills' / name
            if (target.exists() or target.is_symlink()) and not (
                    installed.is_file() and target.is_symlink() and target.resolve() == expected):
                raise ValueError('既存スキルと競合します: ' + str(target))
    if (ROOT / '.codex/hooks.json').exists() and not installed.is_file():
        raise ValueError('既存のプロジェクトhookがあります。上書きせず停止します。')


def run(args, **kwargs):
    subprocess.run([str(x) for x in args], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('zip', type=Path, help='購入者向けの配布ZIP')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        raise ValueError('このプロジェクトのセットアップはmacOS用です。')
    check_conflicts()
    for name in ('uv', 'node', 'ffmpeg', 'ffprobe', 'codex'):
        if not shutil.which(name):
            raise ValueError(f'{name}が必要です。README.mdの前提条件を確認してください。')
    run(['codex', 'login', 'status'])
    digest = verified_zip(args.zip.expanduser().resolve())
    local = ROOT / '.local'
    local.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=local, prefix='verified-') as temporary:
        extract_safe(args.zip.expanduser().resolve(), Path(temporary))
        package = Path(temporary) / f'ai-video-edit-pro-v{VERSION}'
        run([sys.executable, '-B', package / 'package_ops.py', '--package', package])
        saved = local / 'package'
        if saved.exists():
            # 再実行時も、既存の検証済みファイルを黙って上書きしない。
            original = saved / package.name
            run([sys.executable, '-B', original / 'package_ops.py', '--package', original])
        else:
            saved.mkdir()
            shutil.copytree(package, saved / package.name)
    package = local / 'package' / f'ai-video-edit-pro-v{VERSION}'
    uv_env = os.environ.copy()
    uv_env.update(UV_PYTHON_INSTALL_DIR=str(local / 'python'), UV_CACHE_DIR=str(local / 'uv-cache'),
                  UV_PYTHON_BIN_DIR=str(local / 'bin'))
    python = local / 'venv/bin/python'
    if not python.exists():
        run(['uv', 'python', 'install', '3.12.13'], env=uv_env)
        run(['uv', 'venv', '--python', '3.12.13', local / 'venv'], env=uv_env)
    run(['uv', 'pip', 'install', '--python', python, '-r', ROOT / 'requirements.lock',
         '-r', package / 'skills/ai-video-edit/update-requirements.txt',
         'Pillow', 'scikit-learn', 'fonttools', 'opencv-python', 'qrcode', 'zxing-cpp', 'requests'], env=uv_env)
    env = environment()
    run([python, package / 'skills/ai-video-edit/runtime_probe.py', '--smoke'], env=env)
    # 標準インストーラーの--homeをプロジェクトへ向け、認証を迂回しない。
    run([python, package / 'install.py', '--source', package / 'skills', '--home', ROOT, '--host', 'codex'], env=env)
    # ネイティブhookにも同じHOME・Python・データ隔離を適用する。
    hook_path = ROOT / '.codex/hooks.json'
    hooks = json.loads(hook_path.read_text())
    for entries in hooks.get('hooks', {}).values():
        for entry in entries:
            for hook in entry.get('hooks', []):
                command = hook.get('command', '')
                for script in ('stop.py', 'skill_edit.py'):
                    if f'/ai-video-edit/hooks/{script}' in command:
                        hook['command'] = shlex.join([str(python), str(ROOT / 'scripts/aivep.py'),
                                                     str(ROOT / '.ai-video-edit-pro/skills/ai-video-edit/hooks' / script)])
    temporary_hook = hook_path.with_suffix('.json.tmp')
    temporary_hook.write_text(json.dumps(hooks, ensure_ascii=False, indent=2) + '\n')
    temporary_hook.chmod(0o600)
    temporary_hook.replace(hook_path)
    (local / 'verified-sha256.txt').write_text(digest + '\n')
    run([python, ROOT / 'scripts/aivep.py', 'check'])


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'セットアップは未完了です: {error}')
