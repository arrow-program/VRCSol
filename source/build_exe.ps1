# PowerShell ビルドスクリプト
# 使い方:
# 1) 仮想環境を作成し有効化 (任意)
# 2) このディレクトリで `.uild_exe.ps1` を実行

python -m pip install --upgrade pip
pip install pyinstaller python-osc

# --onefile による単一ファイル作成
# windowed にするとコンソールウィンドウが出なくなります（GUI用）
pyinstaller --onefile --windowed --name vrcsol_gui --icon=icon.ico --add-data "settings.json;." gui.py

Write-Host "ビルド完了。dist\vrcsol_gui.exe を確認してください。"