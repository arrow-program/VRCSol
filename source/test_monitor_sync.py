from monitor import Monitor

def print_cb(msg):
    print(msg)

def status_cb(aura, biome):
    print(f"STATUS: {aura} / {biome}")

m = Monitor(message_callback=print_cb, status_callback=status_cb)
# run the monitor logic synchronously (one-shot)
m._run()
print('done')