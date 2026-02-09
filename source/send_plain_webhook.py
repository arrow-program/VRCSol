from monitor import Monitor

WEBHOOK = 'https://discord.com/api/webhooks/1466715578264850487/mku0_KKrUmwrnYot9-oz8PhoH1lEEk-F3rdE_Jsy4InpgiEoOYz5sKhNXX1ZcfHVVrXV'

m = Monitor(message_callback=print, transport='discord', webhook_url=WEBHOOK)
print('Sending plain text to webhook...')
ok = m._post_discord(content='テスト送信: Biome Started - HELL | Equipped: ExampleItem')
print('Result:', ok)
