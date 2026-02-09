from monitor import Monitor

# Use httpbin.org/post as a test endpoint that echoes back requests (not a real Discord webhook)
WEBHOOK = 'https://httpbin.org/post'
JOIN = 'https://example.com/join'

m = Monitor(message_callback=print, status_callback=lambda a,b: print('STATUS',a,b), transport='discord', webhook_url=WEBHOOK, join_url=JOIN, embed_author='fishSol v1.8', thumbnail_url='https://example.com/thumb.png')
# Directly call _post_discord to send an embed + button (bypasses log parsing)
embed = {
    'title': 'Biome Started - TEST',
    'description': 'Equipped: TESTITEM',
    'color': 0xFF4444,
    'timestamp': '2026-01-30T00:00:00Z',
    'footer': {'text': 'vrcsol'},
    'author': {'name': 'fishSol v1.8'},
    'thumbnail': {'url': 'https://example.com/thumb.png'}
}
components = [{
    'type': 1,
    'components': [{
        'type': 2,
        'style': 5,
        'label': 'Join Server',
        'url': JOIN
    }]
}]

print('Sending test payload to', WEBHOOK)
ok = m._post_discord(embed=embed, components=components)
print('Result:', ok)
