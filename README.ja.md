# vrcsol

VRChat の監視と Discord Webhook 統合の GUI アプリケーション。

## 必要環境

- Windows 10 / 11 (64-bit 推奨)
- Python 3.14 以上（ソースから実行する場合）
- python-osc パッケージ

フォルダ構成として、ルートに README と Start GUI ショートカット、ソース一式は `source` フォルダー内に配置されています。

## 起動方法

### 推奨: ショートカットから起動

ルートにある「Start GUI」ショートカットをダブルクリック。

### コマンドラインから実行

PowerShell:

```powershell
cd .\source
.\start_gui.bat
```

あるいはルートから：

```powershell
Start-Process -FilePath '.\source\start_gui.bat'
```

### ソースから開発実行する場合

```powershell
cd .\source
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install python-osc
python gui.py
```

## 設定ファイルのパス

- ユーザー設定: `%APPDATA%\vrcsol\settings.json`
- バイオームメッセージ: `source\biome message.txt`
- アイコン画像: `source\biome icons\`

## 使い方

1. GUI を起動。
2. Transport (OSC / Discord)、Webhook URL、サーバー名などを設定。
3. 「Test Webhook」で送信テスト可能。
4. 「Start」で監視開始、「Stop」で停止。

## トラブルシューティング

- Python が見つからない場合は、仮想環境を作成するか、システムに Python 3.14 以上をインストール。
- Webhook 送信失敗時は、GUI のコンソール出力を確認。

## サポート

不具合や提案は GitHub Issue へ。
