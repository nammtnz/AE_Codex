from pathlib import Path
from PIL import Image, ImageDraw
import sys
folder = Path(sys.argv[1]).resolve()
paths = sorted(folder.glob('c*-mode*.png'))
if not paths: raise RuntimeError('No frames')
sheet = Image.new('RGB', (1200, ((len(paths)+2)//3)*340), '#252530')
draw = ImageDraw.Draw(sheet)
for i, p in enumerate(paths):
    im=Image.open(p).convert('RGB')
    im.thumbnail((390, 305))
    col, row = i%3, i//3
    sheet.paste(im, (col*400+(400-im.width)//2,row*340+25))
    draw.text((col*400+8,row*340+6),p.stem,fill='white')
out=folder/'mode-contact-sheet.jpg'
sheet.save(out, quality=95)
print(out)
