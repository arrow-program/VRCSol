import os
import time
import glob
import json
import re
from pythonosc import udp_client

# --- 設定 ---
OSC_IP = "127.0.0.1"
OSC_PORT = 9000
ROBLOX_LOG_DIR = os.path.expanduser('~\\AppData\\Local\\Roblox\\logs')

# ターゲットとなるログの識別子
TARGET_KEYWORD = "[FLog::Output] [BloxstrapRPC]"

# 送信メッセージのフォーマット
# {}の部分にそれぞれ データ1, データ2 が入ります
# 例: "Origin : SNOWY" と表示されます
MESSAGE_FORMAT = "{} : {}" 
# ------------

def get_latest_log_file(directory):
    list_of_files = glob.glob(os.path.join(directory, '*.log'))
    if not list_of_files:
        return None
    return max(list_of_files, key=os.path.getctime)

def extract_info_from_line(line):
    """
    行から必要な情報を抜き出す関数
    戻り値: (データ1, データ2) のタプル。見つからなければ None
    """
    try:
        # 1. まずキーワードが含まれているか確認
        if TARGET_KEYWORD not in line:
            return None

        # 2. JSON部分を切り出す
        # "[BloxstrapRPC] " の後ろにある最初の "{" から最後までを取得
        json_str_match = re.search(r'(\{.*\})', line)
        if not json_str_match:
            return None
        
        json_str = json_str_match.group(1)
        data_obj = json.loads(json_str)

        # 3. JSON階層をたどってデータを取得
        # 構造: data -> state, data -> largeImage -> hoverText
        rpc_data = data_obj.get("data", {})
        
        # --- データ1の取得 (state: "Equipped \"Origin\"") ---
        raw_state = rpc_data.get("state", "")
        # 正規表現で "Equipped " の後ろのクオーテーションの中身を抜き出す
        # r'Equipped "(.*)"' は「Equipped "」と「"」の間にある文字を取得する意味
        state_match = re.search(r'Equipped "(.*)"', raw_state)
        
        if state_match:
            data1 = state_match.group(1) # 例: Origin
        else:
            # マッチしなかった場合はそのまま使うか、空にする
            data1 = raw_state 

        # --- データ2の取得 (largeImage -> hoverText: "SNOWY") ---
        large_image = rpc_data.get("largeImage", {})
        data2 = large_image.get("hoverText", "Unknown") # 例: SNOWY

        return data1, data2

    except Exception as e:
        # JSONパースエラーなどは無視
        return None

def main():
    client = udp_client.SimpleUDPClient(OSC_IP, OSC_PORT)
    print("最新のRobloxログを監視中...")
    
    latest_log = get_latest_log_file(ROBLOX_LOG_DIR)
    if not latest_log:
        print("ログファイルが見つかりません。")
        return

    print(f"対象ファイル: {os.path.basename(latest_log)}")
    
    last_sent_message = "" # 直前に送ったメッセージを記憶（重複防止用）
    last_sent_time = 0      # 直前に送った時刻（同一内容の再送信用）

    with open(latest_log, 'r', encoding='utf-8', errors='ignore') as f:
        f.seek(0, 2) # 末尾へ移動
        
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            # 抽出処理
            result = extract_info_from_line(line)
            
            if result:
                data1, data2 = result
                
                # チャットボックスに表示する文字列を作成
                message = f"EQUIPPED:{data1} BIOME:{data2}"
                
                now = time.time()
                if message != last_sent_message:
                    client.send_message("/chatbox/input", [message, True])
                    print(f"送信: {message}")
                    last_sent_message = message
                    last_sent_time = now
                else:
                    # 同じ内容の場合は5秒経過後に再送信
                    if now - last_sent_time >= 5:
                        client.send_message("/chatbox/input", [message, True])
                        print(f"再送信: {message}")
                        last_sent_time = now

if __name__ == "__main__":
    main()