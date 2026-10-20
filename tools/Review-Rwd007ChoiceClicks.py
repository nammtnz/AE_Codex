import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

root = Path(__file__).resolve().parents[1]
folder = root / '.ae-codex/inspection/20261013-114156-ad77a86b'
items = json.loads((folder / 'click-review.json').read_text(encoding='utf-8-sig'))
for cid in [671, 811, 1059, 1132]:
    rows = [row for row in items if row['id'] == cid]
    width, height = ((270, 480) if cid in (671, 1059) else (480, 270))
    sheet = Image.new('RGB', (width * 4, (height + 24) * 3), (24, 24, 30))
    draw = ImageDraw.Draw(sheet)
    for n, row in enumerate(rows):
        pic = Image.open(folder / row['file']).convert('RGB')
        pic.thumbnail((width, height))
        x, y = n % 4 * width, n // 4 * (height + 24)
        sheet.paste(pic, (x, y + 24))
        draw.text((x + 5, y + 5), f"click {row['event']} / {row['time']:.3f}s", fill='white')
    sheet.save(folder / f'review-c{cid}.jpg', quality=95)
print('48 frames compiled into four contact sheets')

refined = root / '.ae-codex/inspection/20261013-114550-77cd800f'
sheet = Image.new('RGB', (1200, 1100), (24, 24, 30))
draw = ImageDraw.Draw(sheet)
for rownum, cid in enumerate([671, 811, 1059, 1132]):
    for colnum, event in enumerate([4, 7, 8, 9]):
        original = next(row for row in items if row['id'] == cid and row['event'] == event)
        x, y = original['x'], original['y']
        if event in (8, 9):
            y += 17 * (1 if cid in (671, 1059) else .86)
        pic = Image.open(refined / f'c{cid}-click{event}.png').convert('RGB')
        crop = pic.crop((round(x - 300), round(y - 200), round(x + 300), round(y + 300)))
        crop = crop.resize((300, 250))
        ox, oy = colnum * 300, rownum * 275
        sheet.paste(crop, (ox, oy + 25))
        draw.text((ox + 5, oy + 5), f'comp {cid} / click {event}', fill='white')
sheet.save(refined / 'refined-contacts.jpg', quality=95)
print('16 refined contacts compiled at full source resolution')
