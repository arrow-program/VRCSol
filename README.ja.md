[README.ja.md](https://github.com/user-attachments/files/25292666/README.ja.md)
# vrcsol

Sol's RNGの監視と、VRCOSC、 Discord Webhook 統合の GUI アプリケーション。

## 必要環境

- Windows 10 / 11 (64-bit 推奨)
- Python 3.14 以上（ソースから実行する場合）

フォルダ構成として、ルートに README と Start GUI ショートカット、ソース一式は `source` フォルダー内に配置されています。

## 起動方法

### 推奨: ショートカットから起動

ルートにある「Start GUI」ショートカットをダブルクリック。

初回起動時は自動的に仮想環境が作成され、必要なパッケージがインストールされます。

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

### 手動で仮想環境をセットアップ

初回起動時に自動的にセットアップされますが、手動でセットアップしたい場合：

```powershell
cd .\source
.\setup.bat
```

### ソースから開発実行する場合

```powershell
cd .\source
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r ..\requirements.txt
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
