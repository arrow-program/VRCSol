# vrcsol GUI / ビルド手順

概要:
- `gui.py` : Tkinter を使った簡単なGUI。Start/Stop とログ表示、上部に現在のステータス（Aura / Biome）表示を追加しています。言語切替（English / 日本語）が可能で、デフォルトは English です。
  - **デフォルト設定は exe に埋め込まれます**（`settings.json` をビルドに組み込み）。ユーザーが GUI で変更した設定は `%APPDATA%\\vrcsol\\settings.json` に保存されます（Windows）。
- `monitor.py` : 元の `__main__.py` と同等の監視ロジック（停止可能）を提供します。ログはすべて英語固定で、各ログ行の先頭にタイムスタンプ（YYYY-MM-DD HH:MM:SS）を追加します。

使い方:
1. Python (推奨 3.10+) を用意します。Windows なら仮想環境を推奨。
2. 依存をインストール:
   pip install python-osc
3. GUI を実行:
   python gui.py

.exe化 (PyInstaller):
1. PyInstaller をインストール:
   pip install pyinstaller
2. ワンファイル版を作る例:
   pyinstaller --onefile --windowed --name vrcsol_gui gui.py
3. 出力は `dist\vrcsol_gui.exe`

注意点:
- ウィンドウアプリ（--windowed）にするとコンソールは表示されません。動作ログを確認したい場合は `--windowed` を外してビルドしてください。
- 一部のアンチウイルスが単一exeを誤検出する場合があります。動作確認はビルド後に実行して確かめてください。

変更方針:
- 元の `__main__.py` はそのまま保持しました（監視ロジックは `monitor.py` に分離）。
- 必要があれば `monitor.py` を `__main__.py` のロジックと統合できます。

ご希望なら、実際に `gui.py` を exe にビルドして動作確認（ローカルで）まで実行します。

---

# English: vrcsol GUI / Build Instructions ✅

Overview:
- `gui.py`: A simple Tkinter GUI with Start/Stop and a log display. The current status (Aura / Biome) is shown at the top. Language switching (English / 日本語) is available and **English is the default**.
  - **Default settings are embedded in the executable** (the `settings.json` is included in the build). User changes made via the GUI are saved to `%APPDATA%\\vrcsol\\settings.json` on Windows.
- `monitor.py`: Implements the monitoring logic equivalent to the original `__main__.py` (can be stopped). All logs are in English and each line is prefixed with a timestamp in the format `YYYY-MM-DD HH:MM:SS`.

Usage:
1. Prepare Python (recommended 3.10+). A virtual environment is recommended on Windows.
2. Install dependencies:
   pip install python-osc
3. Run the GUI:
   python gui.py

Packaging to .exe (PyInstaller):
1. Install PyInstaller:
   pip install pyinstaller
2. Example to create a one-file executable:
   pyinstaller --onefile --windowed --name vrcsol_gui gui.py
3. The output will be `dist\\vrcsol_gui.exe`.

Notes:
- The `--windowed` (windowed app) option hides the console. Remove `--windowed` if you want to see runtime logs.
- Some antivirus software may mistakenly flag single-file executables. Please test the built executable after creation.

Design decisions:
- The original `__main__.py` is kept as-is; monitoring logic was split into `monitor.py`.
- If desired, `monitor.py` can be merged back into `__main__.py`.

If you like, I can build the `gui.py` executable locally and verify its behavior for you. 🔧
