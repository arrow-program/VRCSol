import sys
import os
import json
from PySide6.QtWidgets import QApplication, QMessageBox, QLineEdit
from PySide6.QtCore import QFile, Slot, QObject, Signal, QEvent, Qt
from PySide6.QtUiTools import QUiLoader
from PySide6.QtGui import QIcon
from datetime import datetime
import urllib
import urllib.request

# ホットキー監視用のライブラリ
from pynput import keyboard

from monitor import Monitor

# パス設定
UI_FILE_PATH = os.path.join(os.path.dirname(__file__), "main.ui")
USER_CONFIG_DIR = os.path.join(os.getenv('APPDATA') or os.path.expanduser('~/.config'), 'vrcsol')
USER_SETTINGS_FILE = os.path.join(USER_CONFIG_DIR, 'settings.json')
ICON_PATH = os.path.join(os.path.dirname(__file__), "icon.ico")

LANG_NAMES = {'en': 'English', 'ja': '日本語'}
TRANSLATIONS = {
    'en': {
        'osc_ip': 'OSC IP:', 'port': 'Port:', 'start': 'Start', 'stop': 'Stop',
        'status_running': 'Running', 'status_stopped': 'Stopped', 'aura': 'Aura:', 'biome': 'Biome:',
        'port_error_title': 'Port Error', 'port_error_msg': 'Please enter an integer port.',
        'language_label': 'Language:', 'transport_label': 'Send to:', 'webhook_label': 'Discord Webhook:', 
        'join_label': 'Join URL:', 'embed_author_label': 'Server Name:', 'rare_mention_label': 'Rare Biome Mention:', 
        'mention_id_label': 'User/Role ID:'
    },
    'ja': {
        'osc_ip': 'OSC IP:', 'port': 'ポート:', 'start': '開始', 'stop': '停止',
        'status_running': '起動中', 'status_stopped': '停止', 'aura': 'オーラ:', 'biome': 'バイオーム:',
        'port_error_title': 'Portエラー', 'port_error_msg': '整数のポートを入力してください。',
        'language_label': '言語:', 'transport_label': '送信先:', 'webhook_label': 'Discord Webhook:', 
        'join_label': '参加URL:', 'embed_author_label': 'サーバー名:', 'rare_mention_label': 'レアバイオームでメンション:', 
        'mention_id_label': 'ユーザー/ロールID:'
    }
}

class MonitorSignals(QObject):
    """別スレッドで動くMonitorクラスやホットキーから、スレッドセーフにGUIへ通知を送るための中継クラス"""
    log_received = Signal(str)
    status_received = Signal(str, str)
    hotkey_triggered = Signal(str)  # ホットキー用のシグナル ('start' または 'stop')

class App(QObject): # QMainWindow から QObject に変更
    def __init__(self):
        super().__init__()
        
        # .uiファイルのロード
        ui_file = QFile(UI_FILE_PATH)
        if not ui_file.open(QFile.ReadOnly):
            print(f"Cannot open {UI_FILE_PATH}")
            sys.exit(-1)
            
        loader = QUiLoader()
        self.ui = loader.load(ui_file) # 第二引数の self を外して競合を回避
        ui_file.close()
        
        # ウィンドウサイズを.uiファイルの定義に固定
        self.ui.setFixedSize(self.ui.size())
        
        if os.path.exists(ICON_PATH):
            self.ui.setWindowIcon(QIcon(ICON_PATH))

        self.monitor = None
        self.is_running = False
        self.hk_listener = None
        self.signals = MonitorSignals()
        
        # 設定の読み込み
        config = self._load_settings()
        self.lang = config.get('language', 'ja')
        self.transport = config.get('transport', 'osc')
        
        # コンボボックスの初期化
        self.ui.lang_combobox.addItems([LANG_NAMES['ja'], LANG_NAMES['en']])
        self.ui.transport_combobox.addItems(['VRCOSC', 'Discord'])
        self.ui.mention_combobox.addItems(['None', '@everyone', '@here', 'Custom ID'])
        
        # 読み込んだ設定をUIへ反映
        self.ui.ip_entry.setText(config.get('osc_ip', '127.0.0.1'))
        self.ui.port_entry.setText(str(config.get('osc_port', 9000)))
        self.ui.webhook_entry.setText(config.get('webhook_url', ''))
        self.ui.embed_author_entry.setText(config.get('embed_author', ''))
        self.ui.join_entry.setText(config.get('join_url', ''))
        self.ui.mention_id_entry.setText(config.get('mention_id', ''))
        
        # 💡 追加された LineEdit にホットキー設定を反映（デフォルトは f1 / f2）
        self.ui.start_hotkey.setText(config.get('start_hotkey', 'f1'))
        self.ui.stop_hotkey.setText(config.get('stop_hotkey', 'f2'))
        
        m_type = config.get('mention_type', 'none').lower()
        m_map = {'none': 'None', 'everyone': '@everyone', 'here': '@here', 'custom': 'Custom ID'}
        self.ui.mention_combobox.setCurrentText(m_map.get(m_type, 'None'))
        
        self.ui.lang_combobox.setCurrentText(LANG_NAMES.get(self.lang, '日本語'))
        self.ui.transport_combobox.setCurrentText('VRCOSC' if self.transport == 'osc' else 'Discord')

        # シグナル・スロットの接続
        self.ui.lang_combobox.currentIndexChanged.connect(self.on_language_change)
        self.ui.transport_combobox.currentIndexChanged.connect(self.on_transport_change)
        self.ui.mention_combobox.currentIndexChanged.connect(self.on_mention_type_change)
        self.ui.start_btn.clicked.connect(self.start_monitor)
        self.ui.stop_btn.clicked.connect(self.stop_monitor)
        self.ui.test_btn.clicked.connect(self.on_test_webhook)
        
        # 💡 ホットキー入力欄の変更イベントを接続（Enter時、またはフォーカスが外れた時）
        self.ui.start_hotkey.editingFinished.connect(self.update_hotkeys)
        self.ui.stop_hotkey.editingFinished.connect(self.update_hotkeys)
        
        # Monitorスレッドからの通知を受け取るシグナル接続
        self.signals.log_received.connect(self.append_log)
        self.signals.status_received.connect(self.update_status_display)
        
        # ホットキー用のシグナルをスロットに接続
        self.signals.hotkey_triggered.connect(self.handle_hotkey)

        # ウィンドウを閉じる際のイベントを上書きしてフック
        self.ui.closeEvent = self.closeEvent

        # 初期状態反映
        self.on_transport_change()
        self.on_mention_type_change()
        self.apply_language()

        # 💡 ホットキーリスナーの初期登録
        self.update_hotkeys()

        self.ui.installEventFilter(self)

    def eventFilter(self, obj, event):
        """keyPressEventの代わりにeventFilterを使ってキー入力を捕捉する"""
        if event.type() == QEvent.KeyPress:
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                focused_widget = self.ui.focusWidget()
                if isinstance(focused_widget, QLineEdit):
                    focused_widget.clearFocus()
                    return True # イベントを消費して終了
        return super().eventFilter(obj, event)

    def _tr(self, key):
        return TRANSLATIONS.get(self.lang, TRANSLATIONS['ja']).get(key, key)
    

    def apply_language(self):
        """翻訳データに基づいてGUIテキストを書き換える"""
        self.ui.osc_ip_label.setText(self._tr('osc_ip'))
        self.ui.port_label.setText(self._tr('port'))
        self.ui.language_label.setText(self._tr('language_label'))
        self.ui.transport_label.setText(self._tr('transport_label'))
        self.ui.webhook_label.setText(self._tr('webhook_label'))
        self.ui.embed_author_label.setText(self._tr('embed_author_label'))
        self.ui.join_label.setText(self._tr('join_label'))
        self.ui.rare_mention_label.setText(self._tr('rare_mention_label'))
        self.ui.mention_id_label.setText(self._tr('mention_id_label'))
        
        self.ui.start_btn.setText(self._tr('start'))
        self.ui.stop_btn.setText(self._tr('stop'))
        self.ui.aura_label.setText(self._tr('aura'))
        self.ui.biome_label.setText(self._tr('biome'))
        
        if self.is_running:
            self.ui.status_label.setText(self._tr('status_running'))
        else:
            self.ui.status_label.setText(self._tr('status_stopped'))

    def _load_settings(self):
        if os.path.exists(USER_SETTINGS_FILE):
            try:
                with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_settings(self):
        os.makedirs(USER_CONFIG_DIR, exist_ok=True)
        m_map = {'None': 'none', '@everyone': 'everyone', '@here': 'here', 'Custom ID': 'custom'}
        config = {
            'language': self.lang,
            'transport': 'osc' if self.ui.transport_combobox.currentText() == 'VRCOSC' else 'discord',
            'osc_ip': self.ui.ip_entry.text(),
            'osc_port': int(self.ui.port_entry.text()) if self.ui.port_entry.text().isdigit() else 9000,
            'webhook_url': self.ui.webhook_entry.text(),
            'embed_author': self.ui.embed_author_entry.text(),
            'join_url': self.ui.join_entry.text(),
            'mention_type': m_map.get(self.ui.mention_combobox.currentText(), 'none'),
            'mention_id': self.ui.mention_id_entry.text(),
            # 💡 新しいホットキー文字列を保存
            'start_hotkey': self.ui.start_hotkey.text(),
            'stop_hotkey': self.ui.stop_hotkey.text()
        }
        try:
            with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def _format_hotkey(self, key_text):
        """💡 pynputが認識できる形式（例: f1 -> <f1>, ctrl+alt+a -> <ctrl>+<alt>+a）に整形する"""
        key_text = key_text.strip().lower()
        if not key_text:
            return None
            
        # 単体のファンクションキーなどの場合は <> で囲む
        if key_text in ['f1', 'f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 'f12']:
            return f"<{key_text}>"
        return key_text

    @Slot()
    def update_hotkeys(self):
        """💡 ユーザーの入力に合わせてグローバルホットキーの登録をアップデートする"""
        # 既存のリスナーを停止
        if self.hk_listener:
            self.hk_listener.stop()
            self.hk_listener = None

        self._save_settings()

        start_key = self._format_hotkey(self.ui.start_hotkey.text())
        stop_key = self._format_hotkey(self.ui.stop_hotkey.text())

        hotkeys_map = {}
        if start_key:
            hotkeys_map[start_key] = lambda: self.signals.hotkey_triggered.emit('start')
        if stop_key:
            hotkeys_map[stop_key] = lambda: self.signals.hotkey_triggered.emit('stop')

        if hotkeys_map:
            try:
                self.hk_listener = keyboard.GlobalHotKeys(hotkeys_map)
                self.hk_listener.start()
            except Exception as e:
                self.ui.log_text.append(f"[Hotkey] Failed to register hotkeys: {e}")

    @Slot()
    def on_language_change(self):
        self.lang = 'ja' if self.ui.lang_combobox.currentText() == '日本語' else 'en'
        self.apply_language()
        self._save_settings()

    @Slot()
    def on_transport_change(self):
        is_discord = self.ui.transport_combobox.currentText() == 'Discord'
        self.ui.ip_entry.setEnabled(not is_discord)
        self.ui.port_entry.setEnabled(not is_discord)
        self.ui.webhook_entry.setEnabled(is_discord)
        self.ui.embed_author_entry.setEnabled(is_discord)
        self.ui.join_entry.setEnabled(is_discord)
        self.ui.mention_combobox.setEnabled(is_discord)
        self.ui.mention_id_entry.setEnabled(is_discord and self.ui.mention_combobox.currentText() == 'Custom ID')
        self._save_settings()

    @Slot()
    def on_mention_type_change(self):
        is_custom = self.ui.mention_combobox.currentText() == 'Custom ID'
        is_discord = self.ui.transport_combobox.currentText() == 'Discord'
        self.ui.mention_id_entry.setEnabled(is_custom and is_discord)
        self._save_settings()

    @Slot(str)
    def handle_hotkey(self, action):
        """メインスレッド側で安全に開始・停止をハンドリングする"""
        if action == 'start' and not self.is_running:
            self.ui.log_text.append(f"[Hotkey] Start key pressed. Starting monitor...")
            self.start_monitor()
        elif action == 'stop' and self.is_running:
            self.ui.log_text.append(f"[Hotkey] Stop key pressed. Stopping monitor...")
            self.stop_monitor()

    @Slot()
    def start_monitor(self):
        port_text = self.ui.port_entry.text()
        if self.ui.transport_combobox.currentText() == 'VRCOSC' and not port_text.isdigit():
            QMessageBox.critical(self.ui, self._tr('port_error_title'), self._tr('port_error_msg'))
            return

        self._save_settings()
        
        m_map = {'None': 'none', '@everyone': 'everyone', '@here': 'here', 'Custom ID': 'custom'}
        
        self.monitor = Monitor(
            osc_ip=self.ui.ip_entry.text(),
            osc_port=int(port_text) if port_text.isdigit() else 9000,
            transport='osc' if self.ui.transport_combobox.currentText() == 'VRCOSC' else 'discord',
            webhook_url=self.ui.webhook_entry.text(),
            join_url=self.ui.join_entry.text(),
            embed_author=self.ui.embed_author_entry.text(),
            mention_type=m_map.get(self.ui.mention_combobox.currentText(), 'none'),
            mention_id=self.ui.mention_id_entry.text(),
            message_callback=lambda text: self.signals.log_received.emit(text),
            status_callback=lambda d1, d2: self.signals.status_received.emit(d1, d2)
        )
        
        if self.monitor.start():
            self.is_running = True
            self.ui.status_label.setText(self._tr('status_running'))
            self.ui.status_label.setStyleSheet("color: green;")
            self.ui.start_btn.setEnabled(False)
            self.ui.stop_btn.setEnabled(True)

    @Slot()
    def stop_monitor(self):
        if self.monitor:
            self.monitor.stop()
            self.monitor = None
        self.is_running = False
        self.ui.status_label.setText(self._tr('status_stopped'))
        self.ui.status_label.setStyleSheet("color: red;")
        self.ui.start_btn.setEnabled(True)
        self.ui.stop_btn.setEnabled(False)

    @Slot(str)
    def append_log(self, text):
        self.ui.log_text.append(text.strip())

    @Slot(str, str)
    def update_status_display(self, aura, biome):
        self.ui.current_aura_val.setText(aura)
        self.ui.current_biome_val.setText(biome)

    @Slot()
    def on_test_webhook(self):
        import json
        import urllib.request
        import urllib.error
        from datetime import datetime

        webhook_url = self.ui.webhook_entry.text().strip()
        embed_author = self.ui.embed_author_entry.text().strip()

        if not webhook_url:
            self.ui.log_text.append("[Test] Error: Webhook URL is empty.")
            return

        self.ui.log_text.append("[Test] Sending exact test embed to Discord...")

        now = datetime.now()
        time_str = f"{now.year}/{now.month:02d}/{now.day:02d} {now.hour}:{now.minute:02d}"

        embed = {
            "title": "vrcsol Webhook Test",
            "description": "This is a test message from the GUI.",
            "color": 0x00A2FF,
            "footer": {
                "text": f"vrcsol • {time_str}"
            }
        }

        if embed_author:
            embed["author"] = {
                "name": embed_author
            }

        payload = {
            "username": "femboy winter garden",
            "embeds": [embed]
        }

        try:
            json_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=json_data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "vrcsol-client"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                status = response.getcode()
                if status in (200, 204):
                    self.ui.log_text.append("[Test] Test Webhook sent successfully! UwU")
                else:
                    self.ui.log_text.append(f"[Test] Failed. Status code: {status}")

        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="ignore")
            self.ui.log_text.append(f"[Test] HTTP Error {e.code}: {error_body}")
        except Exception as e:
            self.ui.log_text.append(f"[Test] Connection Error: {e}")

    def closeEvent(self, event):
        # アプリ終了時にホットキーリスナーを停止させる
        if self.hk_listener:
            self.hk_listener.stop()
        self.stop_monitor()
        event.accept()

    # 既存のメソッドの後に追記します
    def keyPressEvent(self, event):
        """Enterキーでフォーカス中のQLineEditからフォーカスを外す"""
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            focused_widget = self.focusWidget()
            # フォーカスがあるのがQLineEditの場合のみ外す
            if isinstance(focused_widget, QLineEdit):
                focused_widget.clearFocus()
        else:
            # それ以外のキー操作はデフォルトの挙動を維持
            super().keyPressEvent(event)

def main():
    app = QApplication(sys.argv)
    window = App()
    window.ui.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()