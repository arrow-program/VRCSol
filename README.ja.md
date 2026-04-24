[README.ja.md](https://github.com/user-attachments/files/25292666/README.ja.md)
# vrcsol

Sol's RNG monitoring to VRChat and Discord Webhook integration GUI application.

## 必要要件

- Windows 10 / 11 (64bit 推奨)

## 実行方法

### 推奨: 実行ファイルから起動

1. フォルダ内の **vrcsol.exe** をダブルクリックして実行します。

*注: 初回起動時に Windows SmartScreen の警告が表示される場合は、「詳細情報」をクリックしてから「実行」を選択してください。*

## 設定ファイルのパス

- ユーザー設定: %APPDATA%\vrcsol\settings.json
- バイオームメッセージ: biome message.txt
- アイコン画像: biome icons\

## 使用方法

1. GUIを起動します。
2. Transport (OSC / Discord)、Webhook URL、サーバー名などを設定します。
3. 「Test Webhook」をクリックして送信テストを行います。
4. 「Start」をクリックしてモニタリングを開始し、「Stop」で停止します。

## トラブルシューティング

- アプリが起動しない場合: アンチウイルスソフトによって .exe ファイルがブロックされていないか確認してください。
- Webhookの送信に失敗する場合: GUI内のコンソール出力を確認し、URLが正しいかチェックしてください。

## サポート

不具合報告や提案は GitHub の Issue トラッカーまでお願いします。
