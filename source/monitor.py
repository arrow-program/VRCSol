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
from pythonosc import udp_client

# --- 設定 ---
OSC_IP = "127.0.0.1"
OSC_PORT = 9000
ROBLOX_LOG_DIR = os.path.expanduser('~\\AppData\\Local\\Roblox\\logs')
TARGET_KEYWORD = "[FLog::Output] [BloxstrapRPC]"

MESSAGE_FORMAT = "{} : {}"


def get_latest_log_file(directory):
    list_of_files = glob.glob(os.path.join(directory, '*.log'))
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)


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
    """バックグラウンドでログを監視し、OSC送信するクラス。
    コールバックを使ってGUIにメッセージを渡せます。
    """

    def __init__(self, osc_ip=OSC_IP, osc_port=OSC_PORT, log_dir=ROBLOX_LOG_DIR, message_callback=None, status_callback=None, transport='osc', webhook_url=None, join_url=None, embed_author=None, thumbnail_url=None, mention_type='none', mention_id=''):
        self.osc_ip = osc_ip
        self.osc_port = osc_port
        self.log_dir = log_dir
        self.callback = message_callback
        self.status_callback = status_callback
        self.transport = transport  # 'osc' or 'discord'
        self.webhook_url = webhook_url
        self.join_url = join_url
        self.embed_author = embed_author
        self.thumbnail_url = thumbnail_url
        self.mention_type = mention_type  # 'none', 'everyone', 'here', 'custom'
        self.mention_id = mention_id  # for 'custom' type
        self._stop_event = threading.Event()
        self._thread = None
        self._last_biome_sent = None
        # Load biome messages from file if present
        self._biome_messages = {}
        try:
            self._load_biome_messages()
        except Exception as e:
            # Log exception if callback available
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
            # If embed contains a special key '_local_file_path', attach the file
            file_path = None
            if embed and isinstance(embed, dict) and embed.get('_local_file_path'):
                file_path = embed.pop('_local_file_path')

            headers = {
                'User-Agent': 'vrcsol/1.0'
            }

            if file_path and os.path.exists(file_path):
                # Prepare multipart/form-data with payload_json and file
                boundary = '----vrcsolboundary%08x' % int(time.time() * 1000)
                headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'

                payload_json = json.dumps(payload, ensure_ascii=False).encode('utf-8')
                filename = os.path.basename(file_path)
                ctype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

                parts = []
                parts.append(b'--' + boundary.encode('utf-8'))
                parts.append(b'Content-Disposition: form-data; name="payload_json"')
                parts.append(b'')
                parts.append(payload_json)

                parts.append(b'--' + boundary.encode('utf-8'))
                parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode('utf-8'))
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

            # Log outgoing details for debug
            try:
                self._send_callback(f"Webhook URL: {self.webhook_url}\n")
                self._send_callback(f"Webhook headers: {headers}\n")
                # Truncate payload for log if large
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
        """Return a tuple (start_or_default_message or '', matched_key_or_None).
        Uses exact normalization first, then falls back to partial matches.
        """
        try:
            if not biome_name:
                return '', None
            key = self._normalize_biome_key(biome_name)
            msgs = self._biome_messages.get(key)
            if msgs:
                return msgs.get('start') or msgs.get('default') or '', key
            # fallback: try to match keys that are contained in the biome_name or vice versa
            up = biome_name.strip().upper()
            for k, v in self._biome_messages.items():
                if k in up or up in k:
                    return v.get('start') or v.get('default') or '', k
            return '', None
        except Exception:
            return '', None

    def _is_rare_biome(self, biome_name: str) -> bool:
        """Check if biome is rare (DREAMSPACE, GLITCH, CYBERSPACE)."""
        try:
            rare = {'DREAMSPACE', 'GLITCH', 'CYBERSPACE'}
            return biome_name.upper() in rare
        except Exception:
            return False

    def _get_mention_string(self) -> str:
        """Build mention string based on mention_type and mention_id."""
        try:
            if self.mention_type == 'everyone':
                return '@everyone'
            elif self.mention_type == 'here':
                return '@here'
            elif self.mention_type == 'custom' and self.mention_id:
                # Support both user IDs and role IDs (role IDs start with <@& and user IDs with <@)
                mid = self.mention_id.strip()
                if mid.isdigit():
                    # If it looks like a role ID (common patterns)
                    # We'll try to guess based on length, but default to user mention
                    return f'<@{mid}>'
                return mid
            return ''
        except Exception:
            return ''

    def _load_biome_messages(self):
        """Parse biome message file into dict keyed by normalized biome name.
        File lines format examples:
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
        
        # Check file size
        file_size = os.path.getsize(path)
        self._send_callback(f"File size: {file_size} bytes\n")
        
        with open(path, 'r', encoding='utf-8') as f:
            # Check if file object is readable
            self._send_callback(f"File object mode: {f.mode}, readable: {f.readable()}\n")
            
            lines_read = 0
            for raw in f:
                lines_read += 1
                line = raw.rstrip('\n\r')
                self._send_callback(f"DEBUG line {lines_read}: {repr(line[:80])}\n")
                
                if not line:
                    self._send_callback(f"  -> Empty line\n")
                    continue
                if line.startswith('#'):
                    self._send_callback(f"  -> Comment, skip\n")
                    continue
                
                # Match optional (start)/(end), then [Biome]: message
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

        latest_log = get_latest_log_file(self.log_dir)
        if not latest_log:
            self._send_callback("No log file found.\n")
            return

        self._send_callback(f"Monitor started: {os.path.basename(latest_log)}\n")

        last_sent_message = ""
        last_sent_time = 0

        try:
            with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(0, 2)
                while not self._stop_event.is_set():
                    line = f.readline()
                    if not line:
                        time.sleep(0.1)
                        continue
                    result = extract_info_from_line(line)
                    if result:
                        data1, data2 = result
                        # GUI更新用にステータスを通知
                        self._send_status(data1, data2)
                        message = f"BIOME:{data2}"
                        now = time.time()
                        # If this biome equals the last one we successfully sent to Discord, skip sending
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
                                    # Before sending start for new biome, send end for previous biome if available
                                    # Only for specific biomes that have end messages
                                    try:
                                        prev = self._last_biome_sent
                                        allowed_end_biomes = {'DREAMSPACE', 'GLITCH', 'CYBERSPACE'}
                                        if prev and prev != data2 and prev.upper() in allowed_end_biomes:
                                            # prefer explicit 'end' entry if present
                                            prev_key = self._normalize_biome_key(prev)
                                            prev_msgs = self._biome_messages.get(prev_key, {})
                                            end_msg = prev_msgs.get('end')
                                            if not end_msg:
                                                # fallback to any message available for prev
                                                end_msg, matched_prev = self._get_biome_message(prev)
                                            if end_msg:
                                                end_embed = {
                                                    'title': f"Biome Ended - {prev}",
                                                    'description': end_msg,
                                                    'color': self._biome_color(prev),
                                                    'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                                                    'footer': {'text': 'vrcsol'}
                                                }
                                                # attach icon for prev if exists
                                                try:
                                                    icon_path_prev = self._find_biome_icon(prev)
                                                    if icon_path_prev:
                                                        end_embed['thumbnail'] = {'url': f'attachment://{os.path.basename(icon_path_prev)}'}
                                                        end_embed['_local_file_path'] = icon_path_prev
                                                except Exception:
                                                    pass
                                                # send end embed
                                                self._post_discord(embed=end_embed)
                                    except Exception:
                                        pass

                                    # Build an embed to send for the new biome (start/default)
                                    start_msg, matched = self._get_biome_message(data2)
                                    try:
                                        self._send_callback(f"Resolved biome message for '{data2}': matched={matched} msg={repr(start_msg)}\n")
                                    except Exception:
                                        pass
                                    
                                    # Check if this is a rare biome and prepare mention
                                    mention_str = ''
                                    if self._is_rare_biome(data2):
                                        mention_str = self._get_mention_string()
                                        if mention_str:
                                            try:
                                                self._send_callback(f"Rare biome '{data2}' detected, adding mention: {mention_str}\n")
                                            except Exception:
                                                pass
                                    
                                    embed = {
                                        'title': f"Biome Started - {data2}",
                                        'description': start_msg,
                                        'color': self._biome_color(data2),
                                        'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                                        'footer': {'text': 'vrcsol'}
                                    }
                                    # Optional author and thumbnail
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

                                    # Attach local biome icon if available
                                    try:
                                        icon_path = self._find_biome_icon(data2)
                                        if icon_path:
                                            # Use attachment mechanism: client will attach file and reference it
                                            embed['thumbnail'] = {'url': f'attachment://{os.path.basename(icon_path)}'}
                                            embed['_local_file_path'] = icon_path
                                    except Exception:
                                        pass

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
                                        self._send_callback(f"Sent webhook: {message}\n")
                                        # record last successful biome
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
                                        # Resend embed
                                        embed = {
                                            'title': f"Biome Started - {data2}",
                                            'description': '',
                                            'color': 0xFF4444,
                                            'timestamp': datetime.datetime.utcnow().isoformat() + 'Z',
                                            'footer': {'text': 'vrcsol'}
                                        }
                                        # Optional author and thumbnail
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

                                        # Attach local biome icon if available
                                        try:
                                            icon_path = self._find_biome_icon(data2)
                                            if icon_path:
                                                embed['thumbnail'] = {'url': f'attachment://{os.path.basename(icon_path)}'}
                                                embed['_local_file_path'] = icon_path
                                        except Exception:
                                            pass

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
                                        ok = self._post_discord(embed=embed, components=components)
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
        # Avoid blocking the caller (GUI) by joining in a background daemon thread
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
            # Normalize search
            target = re.sub(r'[^A-Za-z0-9_-]', '', biome_name).lower()
            for fn in os.listdir(icons_dir):
                name, ext = os.path.splitext(fn)
                if not ext:
                    continue
                if name.lower() == target:
                    return os.path.join(icons_dir, fn)
            # Fallback: partial match
            for fn in os.listdir(icons_dir):
                name, ext = os.path.splitext(fn)
                if target in name.lower():
                    return os.path.join(icons_dir, fn)
        except Exception:
            pass
        return None

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
                'CYBERSPACE': 0x06438B
            }
            if not biome_name:
                return 0x000000
            key = biome_name.strip().upper()
            # Some names may be like 'SAND STORM' or 'Sand Storm' etc.
            if key in m:
                return m[key]
            # try more flexible matching
            for k in m.keys():
                if k in key:
                    return m[k]
            return 0xFF4444
        except Exception:
            return 0xFF4444
