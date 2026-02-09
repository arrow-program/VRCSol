import os
import time
import json
from monitor import Monitor

# Test setup
TEST_LOG_DIR = os.path.join(os.getcwd(), "test_logs")
os.makedirs(TEST_LOG_DIR, exist_ok=True)
WEBHOOK = 'https://discord.com/api/webhooks/1466715578264850487/mku0_KKrUmwrnYot9-oz8PhoH1lEEk-F3rdE_Jsy4InpgiEoOYz5sKhNXX1ZcfHVVrXV'

# 1. Create a dummy log file
log_path = os.path.join(TEST_LOG_DIR, f"test_{int(time.time())}.log")
with open(log_path, "w", encoding="utf-8") as f:
    f.write("Initial log line\n")

print(f"Created test log: {log_path}")

# 2. Start Monitor
def log_cb(msg): print(f"[LOG] {msg.strip()}")

m = Monitor(
    log_dir=TEST_LOG_DIR,
    transport='discord',
    webhook_url=WEBHOOK,
    embed_author='vrcsol-E2E-Test',
    message_callback=log_cb
)

print("Starting monitor...")
m.start()
time.sleep(2) # Wait for thread to settle

# 3. Simulate a BloxstrapRPC event in the log
# Format: [FLog::Output] [BloxstrapRPC] {"data":{"state":"Equipped \"HELL-SLAYER\"","largeImage":{"hoverText":"HELL"}}}
rpc_json = {
    "data": {
        "state": 'Equipped "HELL-SLAYER"',
        "largeImage": {"hoverText": "HELL"}
    }
}
log_line = f"2026-01-30T10:00:00.000Z,000001,1,6 [FLog::Output] [BloxstrapRPC] {json.dumps(rpc_json)}\n"

print("Appending new data to log...")
with open(log_path, "a", encoding="utf-8") as f:
    f.write(log_line)
    f.flush()

# 4. Wait for processing and send
print("Waiting for monitor to pick up changes...")
time.sleep(5)

print("Stopping monitor...")
m.stop()
print("Test finished. Check your Discord channel for the 'HELL' biome message.")
