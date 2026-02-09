from monitor import Monitor
import time

def print_cb(msg):
    print(repr(msg))

def status_cb(aura, biome):
    print(f"STATUS: {aura} / {biome}")

m = Monitor(message_callback=print_cb, status_callback=status_cb)
m.start()
# Give it a moment to run
time.sleep(1)
# Stop thread (if running)
m.stop()
print('done')