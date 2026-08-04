import os
import time
import glob
import json
import re
import threading
import urllib.request
import urllib.error
import datetime
import mimetypes
from typing import Optional, Union
from pythonosc import udp_client
import pyautogui as pag 
import win32gui
import win32ui
import win32con
from pathlib import Path
from PIL import ImageGrab  # マルチモニターキャプチャのためにインポート
from ctypes import windll
from PIL import Image, ImageGrab
import traceback


# WindowsのDPIスケーリングによる座標のズレを防ぐため、プロセス単位でDPIアウェアネスを有効化
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- 設定 ---
OSC_IP = "127.0.0.1"
OSC_PORT = 9000
ROBLOX_LOG_DIR = Path.home() / "AppData" / "Local" / "Roblox" / "logs"
TARGET_KEYWORD = "[BloxstrapRPC]"
WINDOWTITLE = "Roblox"
MESSAGE_FORMAT = "{} : {}"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCREENSHOT_DIR = os.path.join(BASE_DIR, "biome screenshot", "screenshot.png")

hwnd = win32gui.FindWindow(None, WINDOWTITLE)


def set_foreground_by_title(WINDOWTITLE):
    hwnd = win32gui.FindWindow(None, WINDOWTITLE)
    win32gui.SetForegroundWindow(hwnd)

def get_latest_log_file(directory):
    directory = Path(directory)
    if not directory.exists():
        return None
    log_files = list(directory.glob('*.log'))
    if not log_files:
        return None
    return max(log_files, key=lambda p: p.stat().st_mtime)


def extract_info_from_line(line):
    try:
        if TARGET_KEYWORD not in line:
            return None
        json_str_match = re.search(r'(\{.*\})', line)
        if not json_str_match:
            return None
        json_str = json_str_match.group(1)
        data_obj = json.loads(json_str)
        rpc_data = data_obj.get("data", {})
        raw_state = rpc_data.get("state", "")
        state_match = re.search(r'Equipped "(.*)"', raw_state)
        if state_match:
            data1 = state_match.group(1)
        else:
            data1 = raw_state
        large_image = rpc_data.get("largeImage", {})
        data2 = large_image.get("hoverText", "Unknown")
        return data1, data2
    except Exception:
        return None


class Monitor:
    """バックグラウンドでログを監視し、OSC メッセージを送信します。
    コールバックを使用して GUI にメッセージを渡します。
    """

    def __init__(self, osc_ip=OSC_IP, osc_port=OSC_PORT, log_dir=ROBLOX_LOG_DIR, message_callback=None, status_callback=None, transport='osc', webhook_url=None, join_url=None, embed_author=None, thumbnail_url=None, mention_type='none', mention_id='', biome_options=None):
        self.osc_ip = osc_ip
        self.osc_port = osc_port
        self.log_dir = log_dir
        self.callback = message_callback
        self.status_callback = status_callback
        self.transport = transport  # 'osc' または 'discord'
        self.webhook_url = webhook_url
        self.join_url = join_url
        self.embed_author = embed_author
        self.thumbnail_url = thumbnail_url
        self.mention_type = mention_type  # 'none', 'everyone', 'here', 'custom'
        self.mention_id = mention_id  # 'custom' タイプ用
        self._stop_event = threading.Event()
        self._thread = None
        self._last_biome_sent = None
        # ファイルからバイオームメッセージを読み込む（存在する場合）
        self._biome_messages = {}

        # バイオームごとのオプション（キーは正規化された大文字英数字）
        self.biome_options = {}
        try:
            if isinstance(biome_options, dict):
                for k, v in biome_options.items():
                    nk = self._normalize_biome_key(k)
                    try:
                        self.biome_options[nk] = {
                            'screenshot': bool(v.get('screenshot', False)),
                            'mention': bool(v.get('mention', False))
                        }
                    except Exception:
                        # 入力が単純な真偽値かもしれない
                        self.biome_options[nk] = {'screenshot': bool(v), 'mention': False}
        except Exception:
            self.biome_options = {}

        try:
            self._load_biome_messages()
        except Exception as e:
            # コールバックが利用可能な場合は例外をログに記録
            try:
                self._send_callback(f"Error loading biome messages: {e}\n")
            except Exception:
                pass

    def _send_callback(self, text: str):
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        if self.callback:
            try:
                self.callback(f"{ts} {text}")
            except Exception:
                pass

    def _send_status(self, data1: str, data2: str):
        if self.status_callback:
            try:
                self.status_callback(data1, data2)
            except Exception:
                pass

    def _post_discord(self, content: str=None, embed: dict=None, components: list=None):
        try:
            payload = {}
            if content:
                payload['content'] = content
            if embed:
                payload['embeds'] = [embed]
            if components:
                payload['components'] = components

            # embedに特殊キー '_local_file_path' または '_local_file_paths' が含まれている場合、複数ファイルを添付可能に拡張
            file_paths = []
            if embed and isinstance(embed, dict):
                if embed.get('_local_file_path'):
                    file_paths.append(embed.pop('_local_file_path'))
                if embed.get('_local_file_paths'):
                    file_paths.extend(embed.pop('_local_file_paths'))

            headers = {
                'User-Agent': 'vrcsol/1.0'
            }

            # 重複を排除し、存在する有効なファイルパスのみをリスト化
            valid_file_paths = []
            for p in file_paths:
                if p and os.path.exists(p) and p not in valid_file_paths:
                    valid_file_paths.append(p)

            if valid_file_paths:
                # payload_jsonと複数のファイルをマルチパート/フォームデータに構築
                boundary = '----vrcsolboundary%08x' % int(time.time() * 1000)
                headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'

                payload_json = json.dumps(payload, ensure_ascii=False).encode('utf-8')
                parts = []
                
                # JSONデータを追加
                parts.append(b'--' + boundary.encode('utf-8'))
                parts.append(b'Content-Disposition: form-data; name="payload_json"')
                parts.append(b'')
                parts.append(payload_json)

                # すべての対象ファイルをフォームデータに格納
                for idx, file_path in enumerate(valid_file_paths):
                    filename = os.path.basename(file_path)
                    ctype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

                    parts.append(b'--' + boundary.encode('utf-8'))
                    parts.append(f'Content-Disposition: form-data; name="file[{idx}]"; filename="{filename}"'.encode('utf-8'))
                    parts.append(f'Content-Type: {ctype}'.encode('utf-8'))
                    parts.append(b'')
                    with open(file_path, 'rb') as fh:
                        file_bytes = fh.read()
                    parts.append(file_bytes)

                parts.append(b'--' + boundary.encode('utf-8') + b'--')
                body = b"\r\n".join(parts) + b"\r\n"
                data = body
            else:
                headers['Content-Type'] = 'application/json'
                data = json.dumps(payload).encode('utf-8')

            # デバッグ用に送信詳細をログに記録
            try:
                self._send_callback(f"Webhook URL: {self.webhook_url}\n")
                self._send_callback(f"Webhook headers: {headers}\n")
                # ペイロードが大きい場合はログ用に切り詰める
                payload_preview = json.dumps(payload, ensure_ascii=False)
                if len(payload_preview) > 2000:
                    payload_preview = payload_preview[:2000] + '...'
                self._send_callback(f"Webhook payload: {payload_preview}\n")
            except Exception:
                pass

            req = urllib.request.Request(self.webhook_url, data=data, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    code = getattr(resp, 'getcode', lambda: None)()
                    if code in (200, 201, 204, None):
                        self._send_callback(f"Discord webhook OK: {code}\n")
                        return True
                    self._send_callback(f"Discord webhook non-OK response: {code}\n")
                    return False
            except urllib.error.HTTPError as he:
                try:
                    body = he.read().decode('utf-8', errors='ignore')
                except Exception:
                    body = '<no body>'
                self._send_callback(f"Discord webhook HTTPError: {he.code} {he.reason}\nResponse body: {body}\n")
                return False
            except urllib.error.URLError as ue:
                self._send_callback(f"Discord webhook URLError: {ue}\n")
                return False
        except Exception as e:
            self._send_callback(f"Discord webhook error: {e}\n")
            return False

    def _normalize_biome_key(self, name: str):
        try:
            return re.sub(r'[^A-Za-z0-9]', '', (name or '').strip()).upper()
        except Exception:
            return (name or '').strip().upper()

    def _get_biome_message(self, biome_name: str):
        """(start_or_default_message または '', matched_key_or_None) のタプルを返します。
        最初に正確な正規化を使用し、次に部分一致にフォールバックします。
        """
        try:
            if not biome_name:
                return '', None
            key = self._normalize_biome_key(biome_name)
            msgs = self._biome_messages.get(key)
            if msgs:
                return msgs.get('start') or msgs.get('default') or '', key
            # フォールバック: biome_nameに含まれるキーまたはその逆を試す
            up = biome_name.strip().upper()
            for k, v in self._biome_messages.items():
                if k in up or up in k:
                    return v.get('start') or v.get('default') or '', k
            return '', None
        except Exception:
            return '', None

    def _is_rare_biome(self, biome_name: str) -> bool:
        """バイオームがレア（DREAMSPACE、GLITCH、CYBERSPACE）かどうかをチェック。
        なお、検出のデバッグには、NORMALを含めます。これをデプロイする前には必ず削除してください。"""
        try:
            rare = {'DREAMSPACE', 'GLITCH', 'CYBERSPACE'}
            return biome_name.upper() in rare
        except Exception:
            return False

    def _get_mention_string(self) -> str:
        """mention_typeとmention_idに基づいてメンション文字列を構築します。"""
        try:
            if self.mention_type == 'everyone':
                return '@everyone'
            elif self.mention_type == 'here':
                return '@here'
            elif self.mention_type == 'custom' and self.mention_id:
                # ユーザーID とロールID の両方をサポート（ロールID は<@&で始まり、ユーザーID は<@で始まる）
                mid = self.mention_id.strip()
                if mid.isdigit():
                    # ロールID のように見える場合（一般的なパターン）
                    # 長さに基づいて推測しますが、ユーザーメンションがデフォルト
                    return f'<@{mid}>'
                return mid
            return ''
        except Exception:
            return ''

    def _load_biome_messages(self):
        """バイオームメッセージファイルを正規化されたバイオーム名をキーとした辞書に解析します。
        ファイル行の形式例：
          [Windy]: message...
          (start) [Dreamspace]: message...
          (end) [Dreamspace]: message...
        """
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, 'biome message.txt')
        if not os.path.exists(path):
            self._send_callback(f"biome message.txt not found at {path}\n")
            return
        self._send_callback(f"Loading biome messages from {path}\n")
        
        # ファイルサイズをチェック
        file_size = os.path.getsize(path)
        self._send_callback(f"File size: {file_size} bytes\n")
        
        with open(path, 'r', encoding='utf-8') as f:
            # ファイルオブジェクトが読み込み可能かチェック
            self._send_callback(f"File object mode: {f.mode}, readable: {f.readable()}\n")
            
            lines_read = 0
            for raw in f:
                lines_read += 1
                line = raw.rstrip('\n\r')
                self._send_callback(f"DEBUG line {lines_read}: {repr(line[:80])}\n")
                
                if not line:
                    self._send_callback(f"  -> 空行\n")
                    continue
                if line.startswith('#'):
                    self._send_callback(f"  -> コメント、スキップ\n")
                    continue
                
                # オプションの(start)/(end)、次に[Biome]: messageに一致
                m = re.match(r'^(?:\((start|end)\)\s*)?\s*\[(.*?)\]\s*:\s*(.*)$', line, re.IGNORECASE)
                if not m:
                    self._send_callback(f"  -> Regex NO MATCH\n")
                    continue
                marker = m.group(1)
                biome = m.group(2)
                msg = m.group(3).strip()
                key = self._normalize_biome_key(biome)
                d = self._biome_messages.setdefault(key, {})
                if marker:
                    if marker.lower() == 'start':
                        d['start'] = msg
                    elif marker.lower() == 'end':
                        d['end'] = msg
                else:
                    d['default'] = msg
                self._send_callback(f"  -> LOADED: key={key} msg={repr(msg[:40])}\n")
        
        self._send_callback(f"Total lines read: {lines_read}\n")
        self._send_callback(f"Total biome messages loaded: {len(self._biome_messages)}\n")
        self._send_callback(f"Biome message keys: {list(self._biome_messages.keys())}\n")

    def _run(self):
        client = None
        if self.transport == 'osc':
            try:
                client = udp_client.SimpleUDPClient(self.osc_ip, self.osc_port)
            except Exception as e:
                self._send_callback(f"Failed to create OSC client: {e}\n")
                return
        elif self.transport == 'discord':
            if not self.webhook_url:
                self._send_callback("No Discord webhook URL configured.\n")
                return

        current_log = get_latest_log_file(self.log_dir)
        if not current_log:
            self._send_callback("No log file found.\n")
            return

        self._send_callback(f"Monitor started: {os.path.basename(current_log)}\n")
        
        # Discord トランスポートを使用している場合、Discord スタート埋め込みを送信
        if self.transport == 'discord':
            try:
                start_embed = {
                    'title': 'Monitor Started',
                    'description': '<t:{0}:R>'.format(int(time.time())),
                    'color': 0x00AA00,
                    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                    'footer': {'text': 'vrcsol'}
                }
                if self.embed_author:
                    start_embed['author'] = {'name': self.embed_author}
                self._post_discord(embed=start_embed)
            except Exception as e:
                self._send_callback(f"Failed to send start embed: {e}\n")

        last_sent_message = ""
        last_sent_time = 0

        try:
            f = open(current_log, 'r', encoding='utf-8', errors='ignore')
            f.seek(0, os.SEEK_END)  # ファイルの末尾に移動して新しい行を待つ              

            while not self._stop_event.is_set():

                    latest = get_latest_log_file(self.log_dir)

                    if latest and latest != current_log:
                        self._send_callback(
                            f"Detected new Roblox log:\n"
                            f"Old: {current_log.name}\n"
                            f"New: {latest.name}\n"
                        )

                        try:
                            f.close()
                        except Exception:
                            pass

                        current_log = latest

                        f = open(current_log, "r", encoding="utf-8", errors="ignore")
                        f.seek(0, os.SEEK_END)

                        self._send_callback(f"Now monitoring {current_log.name}\n")
                        continue

                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    result = extract_info_from_line(line)
                    if result:
                        data1, data2 = result
                        # GUI 更新用にステータスを通知
                        self._send_status(data1, data2)
                        message = f"EQUIPPED:{data1} BIOME:{data2}"
                        now = time.time()
                        # このバイオームが最後に正常に Discord に送信したものと同じ場合、スキップ
                        if self.transport == 'discord' and self._last_biome_sent and data2 == self._last_biome_sent:
                            last_sent_message = message
                            last_sent_time = now
                            continue

                        if message != last_sent_message:
                            try:
                                if self.transport == 'osc':
                                    client.send_message("/chatbox/input", [message, True])
                                    self._send_callback(f"Sent: {message}\n")
                                else:
                                    # 新しいバイオームの開始を送信する前に、使用可能な場合は前のバイオームの終了を送信
                                    # 終了メッセージを持つ特定のバイオームのみ
                                    try:
                                        prev = self._last_biome_sent
                                        allowed_end_biomes = {'DREAMSPACE', 'GLITCH', 'CYBERSPACE'}
                                        if prev and prev != data2 and prev.upper() in allowed_end_biomes:
                                            # 存在する場合は明示的な 'end' エントリを優先
                                            prev_key = self._normalize_biome_key(prev)
                                            prev_msgs = self._biome_messages.get(prev_key, {})
                                            end_msg = prev_msgs.get('end')
                                            if not end_msg:
                                                # 前のバイオーム用に利用可能なメッセージにフォールバック
                                                end_msg, matched_prev = self._get_biome_message(prev)
                                            if end_msg:
                                                end_embed = {
                                                    'title': f"Biome Ended - {prev}",
                                                    'description': end_msg,
                                                    'color': self._biome_color(prev),
                                                    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                                                    'footer': {'text': 'vrcsol'}
                                                }
                                                # 存在する場合は前のバイオームのアイコンを添付
                                                try:
                                                    icon_path_prev = self._find_biome_icon(prev)
                                                    if icon_path_prev:
                                                        end_embed['thumbnail'] = {'url': f'attachment://{os.path.basename(icon_path_prev)}'}
                                                        end_embed['_local_file_path'] = icon_path_prev
                                                except Exception:
                                                    pass
                                                # 終了埋め込みを送信
                                                self._post_discord(embed=end_embed)
                                    except Exception:
                                        pass

                                    # 新しいバイオーム用に送信する埋め込みを構築（開始/デフォルト）
                                    start_msg, matched = self._get_biome_message(data2)
                                    try:
                                        self._send_callback(f"Resolved biome message for '{data2}': matched={matched} msg={repr(start_msg)}\n")
                                    except Exception:
                                        pass
                                    
                                    # バイオーム名に対する UI 設定を確認して、スクショ/メンションの可否を決定
                                    mention_str = ''
                                    screenshot_taken = False

                                    # 優先順: 1) 正規化キーによる完全一致 2) 部分一致 3) 'OTHER' キー
                                    opt = None
                                    try:
                                        key = self._normalize_biome_key(data2)
                                        opt = self.biome_options.get(key)
                                        if not opt:
                                            up = (data2 or '').strip().upper()
                                            for k_opt, v_opt in self.biome_options.items():
                                                if k_opt in up or up in k_opt:
                                                    opt = v_opt
                                                    break
                                        if not opt:
                                            opt = self.biome_options.get('OTHER')
                                    except Exception:
                                        opt = None

                                    # opt がある場合はそれに従う。なければ既存のレア判定にフォールバック
                                    do_mention = False
                                    do_screenshot = False
                                    if opt:
                                        do_screenshot = bool(opt.get('screenshot', False))
                                        do_mention = bool(opt.get('mention', False))
                                    else:
                                        # 互換性のため、もともとの rare 判定に基づく挙動を維持
                                        do_screenshot = self._is_rare_biome(data2)
                                        do_mention = self._is_rare_biome(data2)

                                    if do_mention:
                                        mention_str = self._get_mention_string()

                                    if do_screenshot:
                                        wins = pag.getWindowsWithTitle(WINDOWTITLE)
                                        if wins:
                                            win = wins[0]
                                            if win.isMinimized:
                                                win.restore()

                                            win.activate()
                                            time.sleep(0.4)

                                            region = (win.left, win.top, win.width, win.height)
                                            self._send_callback(f"DEBUG: Screenshot region = {region}\n")
                                            # スクリーンショットを1回だけ確実に行う
                                            if self._focus_and_screenshot(region):
                                                screenshot_taken = True
                                        else:
                                            self._send_callback("Error: Could not find Roblox window for screenshot.\n")
                                    else:
                                        self._send_callback(f"Biome '{data2}' configured to not take screenshot/mention.\n")

                                    embed = {
                                        'title': f"Biome Started - {data2} <t:{int(time.time())}:R>",
                                        'description': f"{start_msg} \n\n**{data1}** equipped." if start_msg else f"**{data1}** equipped.",
                                        'color': self._biome_color(data2),
                                        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                                        'footer': {'text': 'vrcsol'},
                                        'image': {'url': 'attachment://screenshot.png'} if (screenshot_taken) else None
                                    }

                                    # 送信するファイルを蓄積するリストを用意（上書き問題の根本解決）
                                    local_files = []

                                    if screenshot_taken:
                                        if os.path.exists(SCREENSHOT_DIR):
                                            self._send_callback(f"DEBUG: Screenshot exists at {SCREENSHOT_DIR}, size: {os.path.getsize(SCREENSHOT_DIR)} bytes\n")
                                            local_files.append(SCREENSHOT_DIR)
                                        else:
                                            self._send_callback("DEBUG: ERROR - Screenshot file was NOT created.\n")

                                    # 利用可能な場合は参加 URL を追加
                                    if getattr(self, 'join_url', None):
                                        try:
                                            join_link = f"\n [**Join server**\n**Join server**\n**Join server**]({self.join_url})"
                                            embed['description'] = (embed['description'] or '') + join_link
                                        except Exception:
                                            pass
                                    # オプションの著者とサムネイル
                                    if getattr(self, 'embed_author', None):
                                        try:
                                            embed['author'] = {'name': self.embed_author}
                                        except Exception:
                                            pass
                                    if getattr(self, 'thumbnail_url', None):
                                        try:
                                            embed['thumbnail'] = {'url': self.thumbnail_url}
                                        except Exception:
                                            pass

                                    # 利用可能な場合はローカル バイオーム アイコンを添付
                                    try:
                                        icon_path = self._find_biome_icon(data2)
                                        if icon_path:
                                            # 添付メカニズムを使用: クライアントがファイルを添付して参照
                                            embed['thumbnail'] = {'url': f'attachment://{os.path.basename(icon_path)}'}
                                            # アイコンファイルもリストに追加（上書きせずに両方送信）
                                            local_files.append(icon_path)
                                    except Exception:
                                        pass

                                    # 蓄積したファイルリストを送信用の拡張キーにセット
                                    if local_files:
                                        embed['_local_file_paths'] = local_files

                                    ok = self._post_discord(content=mention_str if mention_str else None, embed=embed)
                                    if ok:
                                        self._send_callback(f"Sent webhook: {message}\n")
                                        # 最後に成功したバイオームを記録
                                        try:
                                            self._last_biome_sent = data2
                                        except Exception:
                                            pass
                                last_sent_message = message
                                last_sent_time = now
                            except Exception as e:
                                self._send_callback(f"Send error: {e}\n")
                        else:
                            if now - last_sent_time >= 5:
                                try:
                                    if self.transport == 'osc':
                                        client.send_message("/chatbox/input", [message, True])
                                        self._send_callback(f"Resent: {message}\n")
                                        last_sent_time = now
                                    else:
                                        # 再送時もバイオームごとの設定を尊重する
                                        opt = None
                                        try:
                                            key = self._normalize_biome_key(data2)
                                            opt = self.biome_options.get(key)
                                            if not opt:
                                                up = (data2 or '').strip().upper()
                                                for k_opt, v_opt in self.biome_options.items():
                                                    if k_opt in up or up in k_opt:
                                                        opt = v_opt
                                                        break
                                            if not opt:
                                                opt = self.biome_options.get('OTHER')
                                        except Exception:
                                            opt = None

                                        do_mention = bool(opt.get('mention', False)) if opt else self._is_rare_biome(data2)
                                        do_screenshot = bool(opt.get('screenshot', False)) if opt else self._is_rare_biome(data2)

                                        mention_str = self._get_mention_string() if do_mention else ''

                                        # 再送の埋め込みを作成
                                        embed = {
                                            'title': f"Biome Started - {data2}",
                                            'description': start_msg or '',
                                            'color': 0xFF4444,
                                            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                                            'footer': {'text': 'vrcsol'}
                                        }

                                        # スクリーンショットの存在を確認して添付する
                                        local_files = []
                                        if do_screenshot and os.path.exists(SCREENSHOT_DIR):
                                            local_files.append(SCREENSHOT_DIR)
                                            embed['image'] = {'url': 'attachment://screenshot.png'}

                                        # 利用可能な場合は参加 URL を追加
                                        if getattr(self, 'join_url', None):
                                            try:
                                                join_link = f" [Join server]({self.join_url})"
                                                embed['description'] = embed['description'] + join_link
                                            except Exception:
                                                pass
                                        # オプションの著者とサムネイル
                                        if getattr(self, 'embed_author', None):
                                            try:
                                                embed['author'] = {'name': self.embed_author}
                                            except Exception:
                                                pass
                                        if getattr(self, 'thumbnail_url', None):
                                            try:
                                                embed['thumbnail'] = {'url': self.thumbnail_url}
                                            except Exception:
                                                pass

                                        # 利用可能な場合はローカル バイオーム アイコンを添付
                                        try:
                                            icon_path = self._find_biome_icon(data2)
                                            if icon_path:
                                                embed['thumbnail'] = {'url': f'attachment://{os.path.basename(icon_path)}'}
                                                local_files.append(icon_path)
                                        except Exception:
                                            pass

                                        if local_files:
                                            # 単一ファイルキー互換のためには最初のファイルもセット
                                            if len(local_files) == 1:
                                                embed['_local_file_path'] = local_files[0]
                                            embed['_local_file_paths'] = local_files

                                        components = None
                                        if getattr(self, 'join_url', None):
                                            components = [{
                                                'type': 1,
                                                'components': [{
                                                    'type': 2,
                                                    'style': 5,
                                                    'label': 'Join Server',
                                                    'url': self.join_url
                                                }]
                                            }]

                                        ok = self._post_discord(content=mention_str if mention_str else None, embed=embed, components=components)
                                        if ok:
                                            self._send_callback(f"Resent webhook: {message}\n")
                                            last_sent_time = now
                                            try:
                                                self._last_biome_sent = data2
                                            except Exception:
                                                pass
                                except Exception as e:
                                    self._send_callback(f"Send error: {e}\n")
        except Exception as e:
            self._send_callback(f"Monitoring error: {e}\n")
        finally:
            try:
                f.close()
            except Exception:
                pass

        # Discord トランスポートを使用している場合、Discord ストップ埋め込みを送信
        if self.transport == 'discord':
            try:
                stop_embed = {
                    'title': 'Monitor Stopped',
                    'description': '<t:{0}:R>'.format(int(time.time())),
                    'color': 0xAA0000,
                    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                    'footer': {'text': 'vrcsol'}
                }
                if self.embed_author:
                    stop_embed['author'] = {'name': self.embed_author}
                self._post_discord(embed=stop_embed)
            except Exception as e:
                self._send_callback(f"Failed to send stop embed: {e}\n")

        self._send_callback("Monitor stopped\n")

    def start(self):
        if self._thread and self._thread.is_alive():
            return False
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self, timeout=3.0):
        if not self._thread:
            return False
        self._stop_event.set()
        # バックグラウンド デーモン スレッドで結合して、呼び出し元（GUI）のブロッキングを回避
        try:
            def _join_thread(t, to):
                try:
                    t.join(to)
                except Exception:
                    pass
            waiter = threading.Thread(target=_join_thread, args=(self._thread, timeout), daemon=True)
            waiter.start()
        except Exception:
            pass
        return True

    def _find_biome_icon(self, biome_name: str):
        try:
            base_dir = os.path.dirname(__file__)
            icons_dir = os.path.join(base_dir, 'biome icons')
            if not os.path.isdir(icons_dir):
                return None
            # 検索を正規化
            target = re.sub(r'[^A-Za-z0-9_-]', '', biome_name).lower()
            for fn in os.listdir(icons_dir):
                name, ext = os.path.splitext(fn)
                if not ext:
                    continue
                if name.lower() == target:
                    return os.path.join(icons_dir, fn)
            # フォールバック: 部分一致
            for fn in os.listdir(icons_dir):
                name, ext = os.path.splitext(fn)
                if target in name.lower():
                    return os.path.join(icons_dir, fn)
        except Exception:
            pass
        return None

    def _focus_and_screenshot(self, region):
        try:
            hwnd = win32gui.FindWindow(None, WINDOWTITLE)
            if not hwnd:
                self._send_callback("Roblox window not found.\n")
                return False

            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()

            saveBitmap = win32ui.CreateBitmap()
            saveBitmap.CreateCompatibleBitmap(mfcDC, width, height)

            saveDC.SelectObject(saveBitmap)

            # PW_RENDERFULLCONTENT = 2
            result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 2)

            if result != 1:
                self._send_callback("PrintWindow failed.\n")
                return False

            bmpinfo = saveBitmap.GetInfo()
            bmpstr = saveBitmap.GetBitmapBits(True)

            img = Image.frombuffer(
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )

            os.makedirs(os.path.dirname(SCREENSHOT_DIR), exist_ok=True)
            img.save(SCREENSHOT_DIR)

            win32gui.DeleteObject(saveBitmap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)

            self._send_callback("Screenshot captured using PrintWindow.\n")
            return True

        except Exception:
            self._send_callback(traceback.format_exc())
            return False

    def _biome_color(self, biome_name: str):
        try:
            m = {
                'NORMAL': 0x13AC6C,
                'WINDY': 0x8FF2FA,
                'SNOWY': 0xC4F5F6,
                'RAINY': 0x3C74DD,
                'SAND STORM': 0xEEBE7A,
                'HELL': 0x5C1219,
                'STARFALL': 0x617CD3,
                'HEAVEN': 0xCEB18C,
                'CORRUPTION': 0x773AD7,
                'NULL': 0x000000,
                'DREAMSPACE': 0xD95E9F,
                'GLITCHED': 0x1E4C3F,
                'CYBERSPACE': 0x06438B,
                'SINGULARITY':0xf59842
            }
            if not biome_name:
                return 0x000000
            key = biome_name.strip().upper()
            # Some names may be like 'SAND STORM' or 'Sand Storm' etc.
            if key in m:
                return m[key]
            # より柔軟なマッチングを試す
            for k in m.keys():
                if k in key:
                    return m[k]
            return 0xFF4444
        except Exception:
            return 0xFF4444