from monitor import Monitor

# Real webhook provided by user
WEBHOOK = 'https://discord.com/api/webhooks/1466702458343391252/-QWR91IHnxkD4lXeq0QVNkAa2KrIO1rE7WvcmZkDcGR1Va62FpTjXHNx78VCGDaa3hdx'

m = Monitor(message_callback=print, status_callback=lambda a,b: print('STATUS',a,b), transport='discord', webhook_url=WEBHOOK, embed_author='fishSol v1.8')
embed = {
    'title': 'Biome Started - HELL',
    'description': 'Equipped: ExampleItem',
    'color': 0xFF4444,
    'timestamp': '2026-01-30T00:00:00Z',
    'footer': {'text': 'vrcsol'},
    'author': {'name': 'fishSol v1.8'}
}

print('Sending embed to real webhook...')
ok = m._post_discord(embed=embed)
print('Result:', ok)
