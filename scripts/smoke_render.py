#!/usr/bin/env python3
"""製品と同じnpm依存・Chromeで、1秒の確認用動画を書き出して検査する。"""
import json
from pathlib import Path
import shutil
import subprocess

from aivep import ROOT


def main():
    chrome = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    if not chrome.is_file():
        raise SystemExit('Google Chromeが見つかりません。')
    package = ROOT / '.local/package/ai-video-edit-pro-v2.5.15/skills/taidan-edit/templates/remotion/package.json'
    if not package.is_file():
        raise SystemExit('先にsetup.pyを実行してください。')
    project = ROOT / '.local/smoke-render'
    project.mkdir(parents=True, exist_ok=True)
    shutil.copy2(package, project / 'package.json')
    (project / 'index.tsx').write_text('''import React from 'react';
import {AbsoluteFill, Composition, registerRoot, useCurrentFrame} from 'remotion';
const Test = () => { const frame = useCurrentFrame(); return <AbsoluteFill style={{
  background: '#172c44', color: 'white', justifyContent: 'center', alignItems: 'center',
  fontFamily: 'sans-serif', fontSize: 36, opacity: Math.min(1, (frame + 1) / 10)
}}>AI動画編集PRO / 動作確認</AbsoluteFill>; };
registerRoot(() => <Composition id="SetupCheck" component={Test}
  width={640} height={360} fps={30} durationInFrames={30}/>);
''', encoding='utf-8')
    subprocess.run(['npm', 'install', '--cache', str(ROOT / '.local/npm-cache'), '--no-audit', '--no-fund'],
                   cwd=project, check=True)
    output = project / 'setup-check.mp4'
    subprocess.run([str(project / 'node_modules/.bin/remotion'), 'render', 'index.tsx', 'SetupCheck',
                    str(output), '--codec=h264', '--browser-executable=' + str(chrome), '--concurrency=1'],
                   cwd=project, check=True)
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(output)],
                            capture_output=True, text=True, check=True)
    probe = json.loads(result.stdout)
    video = next(stream for stream in probe['streams'] if stream['codec_type'] == 'video')
    if (video['codec_name'], video['width'], video['height'], int(video['nb_frames'])) != ('h264', 640, 360, 30):
        raise SystemExit('確認動画の形式またはフレーム数が期待と異なります。')
    if abs(float(probe['format']['duration']) - 1) > 0.05:
        raise SystemExit('確認動画の長さが期待と異なります。')
    subprocess.run(['ffmpeg', '-v', 'error', '-i', str(output), '-f', 'null', '-'], check=True)
    print(f'短尺書き出し・全フレームデコード検査: OK ({output})')


if __name__ == '__main__':
    main()
