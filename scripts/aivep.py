#!/usr/bin/env python3
"""プロジェクト専用の環境で、インストール済み製品のPythonコマンドを実行する。"""
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def environment(root=ROOT):
    env = os.environ.copy()
    # 製品のPath.home()だけを隔離し、既存Codex認証は本来の場所を参照する。
    env.setdefault('CODEX_HOME', str(Path.home() / '.codex'))
    env['HOME'] = str(root)
    env['AIVEP_DATA_DIR'] = str(root / '.ai-video-edit-pro/data')
    env['AIVEP_PYTHON'] = str(root / '.local/venv/bin/python')
    env['PATH'] = str(root / '.local/venv/bin') + os.pathsep + env.get('PATH', '')
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    env['PYTHONNOUSERSITE'] = '1'
    env.pop('PYTHONPATH', None)
    env.pop('PYTHONHOME', None)
    return env


def main():
    if len(sys.argv) < 2:
        raise SystemExit('使い方: python3 scripts/aivep.py workflow.py --help（または check）')
    registration = ROOT / '.ai-video-edit-pro/source.json'
    if not registration.is_file():
        raise SystemExit('未導入です。python3 scripts/setup.py <配布ZIP> を実行してください。')
    record = json.loads(registration.read_text())
    skills = ROOT / '.ai-video-edit-pro/skills'
    python = ROOT / '.local/venv/bin/python'
    if Path(record['skills']) != skills or Path(record['python']) != python:
        raise SystemExit('登録先がこのプロジェクトと異なります。移動後は再セットアップが必要です。')
    name = sys.argv[1]
    if name == 'check':
        command = ROOT / '.local/package/ai-video-edit-pro-v2.5.15/check_env.py'
    else:
        command = (skills / 'ai-video-edit' / name).resolve()
        if not command.is_relative_to(skills.resolve()) or command.suffix != '.py':
            raise SystemExit('製品内のPythonファイルだけを指定してください。')
    if not command.is_file():
        raise SystemExit(f'コマンドがありません: {name}')
    os.execve(str(python), [str(python), str(command), *sys.argv[2:]], environment())


if __name__ == '__main__':
    main()
