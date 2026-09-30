# AI動画編集PRO 専用プロジェクト

AI動画編集PRO 2.5.15をCodexで使うためのセットアップです。製品、Python、利用者データ、スキル、hookはこのプロジェクト内に置きます。ホーム配下の共通スキル・hook・Pythonには登録しません。Codexの既存ログインはそのまま参照します。

## 前提条件

macOS（Apple Siliconで検証）、Python 3、uv、Node.js 22.12以上のLTS、ffmpeg / ffprobe、Codex CLI、Google Chromeが必要です。これらのコマンドはCodexから使えるPATHに置いてください。Codex CLIは本人のアカウントでログイン済みである必要があります。Python 3.12とPython依存はセットアップが専用ディレクトリへ取得します。共有環境の自動更新は行いません。

購入者向けの配布ZIPとインターネット接続が必要です。製品ZIPや展開された製品コードは、この公開リポジトリに含めません。

## セットアップ

このディレクトリで実行します。ZIPの場所は手元のダウンロード先に合わせてください。

```sh
python3 scripts/setup.py ~/Downloads/ai-video-edit-pro-v2.5.15.zip
```

公式HTTPSから対象版のSHA-256を取得し、ZIP全体を照合します。パス脱出・シンボリックリンクを拒否して新しい一時ディレクトリへ展開し、製品のファイル検査を通してからインストーラーを実行します。配布物のAGENTS.mdをこのプロジェクトのAGENTS.mdへコピーしません。

初回は製品のメール認証画面がブラウザで開きます。購入後に登録したメールアドレスと、届いたコードを画面へ直接入力してください。認証を迂回しません。認証待ちは最大15分です。中断後は同じコマンドで再開できます。認証情報をチャットへ貼る必要はありません。

既存の同名スキルや別環境の登録と競合する場合は、上書きせず停止します。製品の更新・移動・削除はこのセットアップの対象外です。同じ場所・同じ版での再実行に対応します。

## 利用する

セットアップ後、このディレクトリをCodexで開き直して「AI動画編集PROで動画を編集したい」と依頼してください。プロジェクトの `.agents/skills/` に4つの製品スキルが登録されます。

製品のPythonコマンドは必ず次のラッパーから実行します。カレントディレクトリは変更しないので、案件フォルダでの操作にも使えます。

```sh
python3 scripts/aivep.py check
python3 scripts/aivep.py workflow.py --help
mkdir -p projects/my-video
python3 scripts/aivep.py workflow.py --project projects/my-video init
```

`scripts/aivep.py` の後ろには、製品の `ai-video-edit/` 内のPythonファイルとその引数を指定します。製品が案内する `python3 <このスキル>/workflow.py ...` は、このラッパー呼び出しに置き換えてください。ラッパーが製品用HOME、データディレクトリ、専用Pythonを設定し、製品内の `Path.home()` 参照もこのプロジェクトへ向けます。Codex認証先は既存の `CODEX_HOME`、未指定なら本来のホームの `.codex` を使います。

動画案件・npm依存・Remotion Studioは `projects/<案件名>/` に作成します。素材は `media/`、出力は `output/` に置けます。すべてGit対象外です。完成時は製品の手順に従い、Studio確認と書き出し後の検査、`workflow.py validate` を実行してください。

## ファイル配置

| 場所 | 用途 | Git管理 |
| --- | --- | --- |
| `scripts/`、`tests/`、ドキュメント | セットアップ・実行・検査 | 対象 |
| `.local/` | 検証済み配布物、Python 3.12、venv、キャッシュ | 対象外 |
| `.ai-video-edit-pro/` | 製品正本、認証済み記録、プロファイル、バックアップ | 対象外 |
| `.agents/skills/`、`.codex/skills/` | プロジェクト用スキル登録 | 対象外 |
| `.codex/hooks.json` | プロジェクト用hook | 対象外 |
| `projects/`、`media/`、`output/` | 案件、素材、動画 | 対象外 |

hookの登録とCodexでの信頼・実発火は別です。ネイティブ発火を確認できるまでは、hookだけで完成検査を保証せず、`workflow.py validate` を必ず実行してください。現在の会話のモデルは変更しません。

## 検査

```sh
python3 -m unittest discover -s tests -v
python3 scripts/aivep.py check
python3 scripts/smoke_render.py
```

製品の環境検査には依存確認と文字描画・H.264符号化が含まれます。インストーラーは短い画像・映像・音声の実処理を確認します。`smoke_render.py` は製品と同じnpm依存を `.local/smoke-render/` に導入し、既存Chromeで1秒・30フレームのH.264を出力、全フレームをデコードします。これは実行環境の検査で、実案件の編集品質の検査とは別です。実際の案件用Remotion依存は、案件作成時に個別に導入します。Python依存の検証済み版は `requirements.lock` に固定しています。
