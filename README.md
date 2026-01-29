# vrcsol GUI / ビルド手順

---

## 🇯🇵 日本語版

**vrcsol** は Windows 向けの GUI アプリケーションです。GitHub リリースでは **vrcsol v1.0.exe**（単一の実行ファイル）のみを配布します。

### 🔧 動作環境
- Windows 10 / 11（64-bit 推奨）
- 特別なランタイムは不要（配布された exe に含まれています）

### 🚀 インストールと実行方法
1. GitHub の Releases ページから `vrcsol v1.0.exe` をダウンロードしてください。
2. ダウンロードしたファイルをダブルクリックして起動します。
3. または PowerShell / コマンドプロンプトから実行する場合は、exe のあるディレクトリで次のコマンドを実行します：

   PowerShell:
   ```powershell
   Start-Process -FilePath 'vrcsol v1.0.exe'
   ```

   コマンドプロンプト (CMD):
   ```cmd
   "vrcsol v1.0.exe"
   ```

> ※ ファイル名に空白が含まれるため、引用符で囲むことを推奨します。

### ✅ バージョン確認 / 検証
- 実行中のウィンドウの「ヘルプ」や「バージョン情報」から確認できる場合があります。
- ダウンロードしたファイルのハッシュを確認するには PowerShell で：
  ```powershell
  Get-FileHash -Path 'vrcsol v1.0.exe' -Algorithm SHA256
  ```

### ❗ トラブルシューティング
- 起動しない場合は、PowerShell で直接実行して出力やエラーメッセージを確認してください。
- ウイルス対策ソフトが誤検知することがあります。信頼できるリリースからダウンロードしてください。
- 問題が解決しない場合は GitHub に Issue を作成してください。

---

## 🇺🇸 English

**vrcsol** is a Windows GUI application. On GitHub we publish only the single-file executable **vrcsol v1.0.exe** in the Releases section.

### 🔧 System requirements
- Windows 10 / 11 (64-bit recommended)
- No additional runtime required (Python/runtime bundled in the distributed exe)

### 🚀 How to install & run
1. Download `vrcsol v1.0.exe` from the GitHub Releases page.
2. Start by double-clicking the downloaded file.
3. Or run from PowerShell / Command Prompt:

   PowerShell:
   ```powershell
   Start-Process -FilePath 'vrcsol v1.0.exe'
   ```

   Command Prompt (CMD):
   ```cmd
   "vrcsol v1.0.exe"
   ```

> Note: The filename contains a space—use quotes when running from a shell.

### ✅ Verify version / checksum
- Check the application's About/Version menu if available.
- To verify checksum (SHA256) in PowerShell:
  ```powershell
  Get-FileHash -Path 'vrcsol v1.0.exe' -Algorithm SHA256
  ```

### ❗ Troubleshooting
- If it does not start, run it from PowerShell to see console output and errors.
- Some antivirus products might flag unsigned executables; download only from the official Releases page.
- If the problem persists, please open an Issue on the project's GitHub repository.

---

## 📄 License & Support
- ソースコードはリポジトリに含まれています（開発者向け）。
- バグ報告やサポートは GitHub の Issue をご利用ください。

---

**簡単なヒント / Quick tip**: リリースページに `vrcsol v1.0.exe` 以外のファイルをアップロードしないでください（公式配布物は exe 単体のみです）。

---

問題や改善提案があれば Issue を作成してください。 ✅

