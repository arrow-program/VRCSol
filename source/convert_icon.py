from PIL import Image
import os

src = os.path.join(os.path.dirname(__file__), 'icon.png')
out = os.path.join(os.path.dirname(__file__), 'icon.ico')

try:
    if not os.path.exists(src):
        print('icon.png not found')
    else:
        img = Image.open(src).convert('RGBA')
        # Ensure we have enough size by resizing larger versions from the source
        sizes = [(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)]
        icons = []
        for s in sizes:
            icons.append(img.resize(s, Image.LANCZOS))
        icons[0].save(out, format='ICO', sizes=[(s[0], s[1]) for s in sizes])
        print('icon.ico created')
except Exception as e:
    print('icon conversion failed:', e)