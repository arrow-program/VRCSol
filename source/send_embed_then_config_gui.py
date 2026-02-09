import os
import json
from monitor import Monitor

# User-provided webhook
WEBHOOK = 'https://discord.com/api/webhooks/1466715578264850487/mku0_KKrUmwrnYot9-oz8PhoH1lEEk-F3rdE_Jsy4InpgiEoOYz5sKhNXX1ZcfHVVrXV'

# Settings to write for GUI
user_config_dir = os.path.join(os.getenv('APPDATA') or os.path.expanduser('~/.config'), 'vrcsol')
user_settings_file = os.path.join(user_config_dir, 'settings.json')

settings = {
    'language': 'en',
    'transport': 'discord',
    'webhook': WEBHOOK,
    'join_url': '',
    'embed_author': 'fishSol v1.8',
    'thumbnail': 'https://example.com/thumb.png',
    'osc_ip': '127.0.0.1',
    'osc_port': 9000
}

os.makedirs(user_config_dir, exist_ok=True)
with open(user_settings_file, 'w', encoding='utf-8') as f:
    json.dump(settings, f, ensure_ascii=False, indent=2)
print('Saved GUI settings to', user_settings_file)

# Send a test embed (no join button)
m = Monitor(message_callback=print, transport='discord', webhook_url=WEBHOOK, embed_author=settings['embed_author'], thumbnail_url=settings['thumbnail'])
embed = {
    'title': 'Biome Started - HELL',
    'description': 'Equipped: ExampleItem',
    'color': 0xFF4444,
    'timestamp': '2026-01-30T00:00:00Z',
    'footer': {'text': 'vrcsol'},
    'author': {'name': settings['embed_author']},
    'thumbnail': {'url': settings['thumbnail']}
}
print('Sending embed to webhook...')
ok = m._post_discord(embed=embed)
print('Embed send result:', ok)

# Instruction for next step
if ok:
    print('\nEmbed sent successfully. You can now open the GUI and press Start to run the monitor; settings are prefilled.\n')
else:
    print('\nEmbed send failed. Check logs above for details.\n')
