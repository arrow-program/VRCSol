import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import os
import json
import time
import datetime
from monitor import Monitor

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "settings.json")
# ユーザーが書き込み可能な設定位置（実行間で永続的、exe 対応）
USER_CONFIG_DIR = os.path.join(os.getenv('APPDATA') or os.path.expanduser('~/.config'), 'vrcsol')
USER_SETTINGS_FILE = os.path.join(USER_CONFIG_DIR, 'settings.json')
ICON_PATH = "./icon.ico"
LANG_NAMES = {'en': 'English', 'ja': '日本語'}
TRANSLATIONS = {
    'en': {
        'osc_ip': 'OSC IP:', 'port': 'Port:', 'start': 'Start', 'stop': 'Stop',
        'status_running': 'Running', 'status_stopped': 'Stopped', 'aura': 'Aura:', 'biome': 'Biome:',
        'port_error_title': 'Port Error', 'port_error_msg': 'Please enter an integer port.',
        'language_label': 'Language:', 'transport_label': 'Send to:', 'webhook_label': 'Discord Webhook:', 'join_label': 'Join URL:', 'embed_author_label': 'Server Name:', 'rare_mention_label': 'Rare Biome Mention:', 'mention_id_label': 'User/Role ID:'
    },
    'ja': {
        'osc_ip': 'OSC IP:', 'port': 'Port:', 'start': '開始', 'stop': '停止',
        'status_running': '起動中', 'status_stopped': '停止', 'aura': 'オーラ:', 'biome': 'バイオーム:',
        'port_error_title': 'Portエラー', 'port_error_msg': '整数のポートを入力してください。',
        'language_label': '言語:', 'transport_label': '送信先:', 'webhook_label': 'Discord Webhook:', 'join_label': 'Join URL:', 'embed_author_label': 'サーバー名:', 'rare_mention_label': 'レアバイオームでメンション:', 'mention_id_label': 'ユーザー/ロールID:'
    }
}   

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("vrcsol GUI")
        self.geometry("650x500")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.iconbitmap(ICON_PATH)
        

        self.monitor = None

        # 現在のステータス（オーラ・バイオーム）
        self.current_aura = tk.StringVar(value="Unknown")
        self.current_biome = tk.StringVar(value="Unknown")

        # 設定と実行状態
        config = self._load_settings()
        self.lang = config.get('language', 'en')
        self.transport = config.get('transport', 'osc')
        self.webhook = config.get('webhook', '')
        self.join_url = config.get('join_url', '')
        # サーバー名設定（設定に「server_name」として保存）
        self.embed_author = config.get('embed_author', '')
        self.osc_ip = config.get('osc_ip', '127.0.0.1')
        self.osc_port = config.get('osc_port', 9000)
        self.mention_type = config.get('mention_type', 'none')
        self.mention_id = config.get('mention_id', '')
        self.is_running = False

        self._build()
        self.apply_language()

    def _build(self):
        frame = ttk.Frame(self)
        frame.pack(fill=tk.X, padx=8, pady=8)

        self.ip_label = ttk.Label(frame, text=self._tr('osc_ip'))
        self.ip_label.grid(row=0, column=0, sticky=tk.W)
        self.ip_entry = ttk.Entry(frame, width=15)
        self.ip_entry.insert(0, self.osc_ip)
        self.ip_entry.grid(row=0, column=1, sticky=tk.W)

        self.port_label = ttk.Label(frame, text=self._tr('port'))
        self.port_label.grid(row=0, column=2, sticky=tk.W, padx=(10,0))
        self.port_entry = ttk.Entry(frame, width=6)
        self.port_entry.insert(0, str(self.osc_port))
        self.port_entry.grid(row=0, column=3, sticky=tk.W)

        # 言語セレクタ
        self.language_label = ttk.Label(frame, text=self._tr('language_label'))
        self.language_label.grid(row=0, column=4, sticky=tk.W, padx=(10,0))
        self.lang_combobox = ttk.Combobox(frame, values=[LANG_NAMES['en'], LANG_NAMES['ja']], width=8, state='readonly')
        self.lang_combobox.set(LANG_NAMES.get(self.lang, LANG_NAMES['en']))
        self.lang_combobox.grid(row=0, column=5, sticky=tk.W)
        self.lang_combobox.bind('<<ComboboxSelected>>', self.on_language_change)

        # トランスポート セレクタと Discord webhook エントリ（行 1）
        self.transport_label = ttk.Label(frame, text=self._tr('transport_label'))
        self.transport_label.grid(row=1, column=0, sticky=tk.W, pady=(6,0))
        self.transport_combobox = ttk.Combobox(frame, values=['VRCOSC', 'Discord'], width=10, state='readonly')
        self.transport_combobox.set('VRCOSC' if self.transport == 'osc' else 'Discord')
        self.transport_combobox.grid(row=1, column=1, sticky=tk.W, padx=(0,10), pady=(6,0))
        self.transport_combobox.bind('<<ComboboxSelected>>', self.on_transport_change)

        self.webhook_label = ttk.Label(frame, text=self._tr('webhook_label'))
        self.webhook_label.grid(row=1, column=2, sticky=tk.W, pady=(6,0))
        self.webhook_entry = ttk.Entry(frame, width=50)
        self.webhook_entry.insert(0, self.webhook)
        self.webhook_entry.grid(row=1, column=3, columnspan=5, sticky=tk.W, pady=(6,0))

        # 埋め込み作成者と参加 URL（行 2）
        self.embed_author_label = ttk.Label(frame, text=self._tr('embed_author_label'))
        self.embed_author_label.grid(row=2, column=0, sticky=tk.W, pady=(6,0))
        self.embed_author_entry = ttk.Entry(frame, width=24)
        self.embed_author_entry.insert(0, self.embed_author)
        self.embed_author_entry.grid(row=2, column=1, sticky=tk.W, pady=(6,0))

        self.join_label = ttk.Label(frame, text=self._tr('join_label'))
        self.join_label.grid(row=2, column=2, sticky=tk.W, pady=(6,0))
        self.join_entry = ttk.Entry(frame, width=40)
        self.join_entry.insert(0, self.join_url)
        self.join_entry.grid(row=2, column=3, columnspan=5, sticky=tk.W, pady=(6,0))
        
        # テスト webhook ボタン（手動送信）
        self.test_webhook_btn = ttk.Button(frame, text='Test Webhook', command=self.on_test_webhook)
        self.test_webhook_btn.grid(row=3, column=3, sticky=tk.W, pady=(6,0))
        
        # メンション設定（行 4）- レアバイオームのみ
        self.rare_mention_label = ttk.Label(frame, text=self._tr('rare_mention_label'))
        self.rare_mention_label.grid(row=4, column=0, sticky=tk.W, pady=(6,0))
        self.mention_combobox = ttk.Combobox(frame, values=['None', '@everyone', '@here', 'Custom ID'], width=15, state='readonly')
        mention_display = {
            'none': 'None',
            'everyone': '@everyone',
            'here': '@here',
            'custom': 'Custom ID'
        }
        self.mention_combobox.set(mention_display.get(self.mention_type, 'None'))
        self.mention_combobox.grid(row=4, column=1, sticky=tk.W, padx=(0,10), pady=(6,0))
        self.mention_combobox.bind('<<ComboboxSelected>>', self.on_mention_type_change)
        
        self.mention_id_label = ttk.Label(frame, text=self._tr('mention_id_label'))
        self.mention_id_label.grid(row=4, column=2, sticky=tk.W, pady=(6,0))
        self.mention_id_entry = ttk.Entry(frame, width=30)
        self.mention_id_entry.insert(0, self.mention_id)
        self.mention_id_entry.grid(row=4, column=3, columnspan=2, sticky=tk.W, pady=(6,0))
        
        # カスタムでない場合は最初は mention_id_entry を無効化
        if self.mention_type != 'custom':
            self.mention_id_entry.config(state='disabled')
        
        # 行 5 の高さを大きなボタン用に設定（デフォルトの 4 倍）
        frame.rowconfigure(5, minsize=80)
        
        # 開始と停止ボタン（行 5）- 他のコントロール下の大きなボタン
        self.stop_btn = ttk.Button(frame, text=self._tr('stop'), command=self.stop_monitor, state=tk.DISABLED, width=24)
        self.stop_btn.grid(row=5, column=0, columnspan=2, sticky=tk.NSEW, pady=(12,6), padx=(5,0))

        self.start_btn = ttk.Button(frame, text=self._tr('start'), command=self.start_monitor, width=24)
        self.start_btn.grid(row=5, column=3, columnspan=3, sticky=tk.NSEW, pady=(12,6), padx=(0,6))
        
        # トランスポート/ウィジェット状態を設定
        try:
            self.on_transport_change()
        except Exception:
            pass

        # ステータス表示（上半分）: オーラ・バイオーム
        status_frame = ttk.Frame(self)
        status_frame.pack(fill=tk.X, padx=8, pady=(4,2))
        self.aura_label = ttk.Label(status_frame, text=self._tr('aura'))
        self.aura_label.grid(row=0, column=0, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.current_aura, font=("TkDefaultFont", 12, "bold")).grid(row=0, column=1, sticky=tk.W, padx=(4,20))
        self.biome_label = ttk.Label(status_frame, text=self._tr('biome'))
        self.biome_label.grid(row=0, column=2, sticky=tk.W)
        ttk.Label(status_frame, textvariable=self.current_biome, font=("TkDefaultFont", 12, "bold")).grid(row=0, column=3, sticky=tk.W)

        self.status_label = ttk.Label(self, text=self._tr('status_stopped'), foreground="red")
        self.status_label.pack(anchor=tk.W, padx=8)

        # ログ（下半分）
        self.log_text = scrolledtext.ScrolledText(self, state='disabled', height=12)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=(4,8))

    def append_log(self, text):
        def _append():
            self.log_text.configure(state='normal')
            self.log_text.insert(tk.END, text)
            self.log_text.see(tk.END)
            self.log_text.configure(state='disabled')
        self.after(0, _append)

    def update_status(self, aura, biome):
        def _update():
            self.current_aura.set(aura)
            self.current_biome.set(biome)
        self.after(0, _update)

    def _load_settings(self):
        # キー付き辞書を返す: language, transport, webhook, osc_ip, osc_port, mention_type, mention_id
        # 優先順位:
        # 1) %APPDATA% のユーザー設定（永続的）
        # 2) 埋め込まれたデフォルト設定（exe またはプロジェクトにバンドル）
        # 3) ハードコードされたデフォルト
        try:
            if os.path.exists(USER_SETTINGS_FILE):
                with open(USER_SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    return {
                        'language': d.get('language', 'en'),
                        'transport': d.get('transport', 'osc'),
                        'webhook': d.get('webhook', ''),
                        'osc_ip': d.get('osc_ip', '127.0.0.1'),
                        'osc_port': d.get('osc_port', 9000),
                        'join_url': d.get('join_url', ''),
                        'embed_author': d.get('embed_author', ''),
                        'mention_type': d.get('mention_type', 'none'),
                        'mention_id': d.get('mention_id', '')
                    }
        except Exception:
            pass

        # 埋め込まれたデフォルトを読み込もうとする（PyInstaller にバンドルされている場合は sys._MEIPASS にある）
        try:
            if getattr(sys, 'frozen', False):
                embedded_path = os.path.join(sys._MEIPASS, 'settings.json')
            else:
                embedded_path = SETTINGS_FILE
            if os.path.exists(embedded_path):
                with open(embedded_path, 'r', encoding='utf-8') as f:
                    d = json.load(f)
                    return {
                        'language': d.get('language', 'en'),
                        'transport': d.get('transport', 'osc'),
                        'webhook': d.get('webhook', ''),
                        'osc_ip': d.get('osc_ip', '127.0.0.1'),
                        'osc_port': d.get('osc_port', 9000),
                        'join_url': d.get('join_url', ''),
                        'embed_author': d.get('embed_author', ''),
                        'mention_type': d.get('mention_type', 'none'),
                        'mention_id': d.get('mention_id', '')
                    }
        except Exception:
            pass

        return {'language': 'en', 'transport': 'osc', 'webhook': '', 'osc_ip': '127.0.0.1', 'osc_port': 9000, 'join_url': '', 'embed_author': '', 'mention_type': 'none', 'mention_id': ''}    

    def _save_settings(self):
        try:
            os.makedirs(USER_CONFIG_DIR, exist_ok=True)
            # メンション コンボボックスの表示を設定値にマップ
            mention_map = {
                'None': 'none',
                '@everyone': 'everyone',
                '@here': 'here',
                'Custom ID': 'custom'
            }
            data = {
                'language': self.lang,
                'transport': getattr(self, 'transport', 'osc'),
                'webhook': self.webhook_entry.get().strip() if hasattr(self, 'webhook_entry') else getattr(self, 'webhook', ''),
                'join_url': self.join_entry.get().strip() if hasattr(self, 'join_entry') else getattr(self, 'join_url', ''),
                'embed_author': self.embed_author_entry.get().strip() if hasattr(self, 'embed_author_entry') else getattr(self, 'embed_author', ''),
                'osc_ip': self.ip_entry.get().strip(),
                'osc_port': int(self.port_entry.get().strip()) if self.port_entry.get().strip().isdigit() else self.osc_port,
                'mention_type': mention_map.get(self.mention_combobox.get() if hasattr(self, 'mention_combobox') else 'None', 'none'),
                'mention_id': self.mention_id_entry.get().strip() if hasattr(self, 'mention_id_entry') else ''
            }
            with open(USER_SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _tr(self, key):
        return TRANSLATIONS.get(self.lang, TRANSLATIONS['en']).get(key, key)

    def apply_language(self):
        # 現在の言語に従って UI テキストを更新
        self.ip_label.config(text=self._tr('osc_ip'))
        self.port_label.config(text=self._tr('port'))
        self.start_btn.config(text=self._tr('start'))
        self.stop_btn.config(text=self._tr('stop'))
        self.aura_label.config(text=self._tr('aura'))
        self.biome_label.config(text=self._tr('biome'))
        # ステータス テキストを更新
        self.status_label.config(text=self._tr('status_running') if self.is_running else self._tr('status_stopped'))
        # コンボボックス表示を更新
        try:
            self.lang_combobox.set(LANG_NAMES.get(self.lang, LANG_NAMES['en']))
        except Exception:
            pass
        # トランスポート/webhook ラベルを更新
        try:
            self.language_label.config(text=self._tr('language_label'))
            self.transport_label.config(text=self._tr('transport_label'))
            self.webhook_label.config(text=self._tr('webhook_label'))
            self.join_label.config(text=self._tr('join_label'))
            self.embed_author_label.config(text=self._tr('embed_author_label'))
            self.rare_mention_label.config(text=self._tr('rare_mention_label'))
            self.mention_id_label.config(text=self._tr('mention_id_label'))
        except Exception:
            pass

    def on_language_change(self, event=None):
        sel = self.lang_combobox.get()
        self.lang = 'en' if sel == LANG_NAMES['en'] else 'ja'
        self._save_settings()
        self.apply_language()

    def on_transport_change(self, event=None):
        sel = self.transport_combobox.get()
        self.transport = 'osc' if sel == 'VRCOSC' else 'discord'
        # enable/disable relevant widgets
        if self.transport == 'discord':
            self.ip_entry.config(state='disabled')
            self.port_entry.config(state='disabled')
            self.webhook_entry.config(state='normal')
            self.join_entry.config(state='normal')
            try:
                self.embed_author_entry.config(state='normal')
            except Exception:
                pass
            try:
                if hasattr(self, 'test_webhook_btn'):
                    self.test_webhook_btn.config(state='normal')
            except Exception:
                pass
        else:
            self.ip_entry.config(state='normal')
            self.port_entry.config(state='normal')
            self.webhook_entry.config(state='disabled')
            self.join_entry.config(state='disabled')
            try:
                self.embed_author_entry.config(state='disabled')
            except Exception:
                pass
            try:
                if hasattr(self, 'test_webhook_btn'):
                    self.test_webhook_btn.config(state='disabled')
            except Exception:
                pass
        self._save_settings()

    def on_mention_type_change(self, event=None):
        selected = self.mention_combobox.get()
        if selected == 'Custom ID':
            self.mention_id_entry.config(state='normal')
        else:
            self.mention_id_entry.config(state='disabled')
        self._save_settings()

    def log_message_en(self, msg):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        self.append_log(f"{ts} {msg}\n")

    def start_monitor(self):
        if self.monitor:
            self.log_message_en("Monitor already running.")
            return

        # Determine transport
        self.transport = 'osc' if (self.transport_combobox.get() == 'VRCOSC') else 'discord'

        if self.transport == 'discord':
            webhook = self.webhook_entry.get().strip()
            if not webhook:
                messagebox.showerror('Webhook Error', 'Please enter a Discord webhook URL.')
                return

            join = self.join_entry.get().strip() if hasattr(self, 'join_entry') else ''
            embed_author = self.embed_author_entry.get().strip() if hasattr(self, 'embed_author_entry') else ''
            thumbnail = self.thumbnail_entry.get().strip() if hasattr(self, 'thumbnail_entry') else ''
            
            # Get mention settings
            mention_map = {
                'None': 'none',
                '@everyone': 'everyone',
                '@here': 'here',
                'Custom ID': 'custom'
            }
            mention_type = mention_map.get(self.mention_combobox.get() if hasattr(self, 'mention_combobox') else 'None', 'none')
            mention_id = self.mention_id_entry.get().strip() if hasattr(self, 'mention_id_entry') else ''
            
            self.monitor = Monitor(message_callback=self.append_log, status_callback=self.update_status, transport='discord', webhook_url=webhook, join_url=join, embed_author=embed_author, thumbnail_url=thumbnail, mention_type=mention_type, mention_id=mention_id)
        else:
            ip = self.ip_entry.get().strip()
            try:
                port = int(self.port_entry.get().strip())
            except ValueError:
                messagebox.showerror(self._tr('port_error_title'), self._tr('port_error_msg'))
                return
            self.monitor = Monitor(osc_ip=ip, osc_port=port, message_callback=self.append_log, status_callback=self.update_status, transport='osc')

        started = self.monitor.start()
        if started:
            self.is_running = True
            self.status_label.config(text=self._tr('status_running'), foreground='green')
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            # Monitor will emit a timestamped "Monitor started" message itself; we can also note the request
            self.log_message_en("Monitor requested to start.")
        else:
            self.log_message_en("Monitor already running.")
    def stop_monitor(self):
        if not self.monitor:
            return
        self.monitor.stop()
        self.monitor = None
        self.is_running = False
        self.status_label.config(text=self._tr('status_stopped'), foreground='red')
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.log_message_en("Monitor stopped.")
        # ステータスをリセット
        self.current_aura.set("Unknown")
        self.current_biome.set("Unknown")

    def on_test_webhook(self):
        webhook = self.webhook_entry.get().strip() if hasattr(self, 'webhook_entry') else getattr(self, 'webhook', '')
        if not webhook:
            messagebox.showerror('Webhook Error', 'Please enter a Discord webhook URL.')
            return

        join = self.join_entry.get().strip() if hasattr(self, 'join_entry') else ''
        embed_author = self.embed_author_entry.get().strip() if hasattr(self, 'embed_author_entry') else ''

        # Create a temporary Monitor instance for sending the test webhook
        m = Monitor(message_callback=self.append_log, status_callback=None, transport='discord', webhook_url=webhook, join_url=join, embed_author=embed_author, thumbnail_url=None)

        embed = {
            'title': 'vrcsol Webhook Test',
            'description': 'This is a test message from the GUI.',
            'color': 0x00AAFF,
            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
            'footer': {'text': 'vrcsol'}
        }
        if embed_author:
            embed['author'] = {'name': embed_author}

        ok = m._post_discord(embed=embed)
        self.log_message_en(f"Test webhook send result: {ok}")
        if ok:
            messagebox.showinfo('Webhook Test', 'Test webhook sent successfully.')
        else:
            messagebox.showerror('Webhook Test', 'Test webhook failed. See log for details.')

    def on_close(self):
        if self.monitor:
            self.monitor.stop()
        self._save_settings()
        self.destroy()


def main():
    app = App()
    app.mainloop()

if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback, sys
        traceback.print_exc()
        try:
            input('エラーが発生しました。Enterキーを押して終了します...')
        except Exception:
            pass
        # re-raise to ensure non-zero exit code for calling batch
        raise
