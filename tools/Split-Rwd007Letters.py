from pathlib import Path
import json
from PIL import Image

root = Path(__file__).resolve().parents[1]
folder = root / 'assets/rwd007-win/letters13'
im = Image.open(folder / 'level-complete-letter-sheet.png').convert('RGBA')
if im.getchannel('A').getextrema()[0] == 255:
    raise RuntimeError('Generated sheet lacks transparent pixels')
letters = 'LEVELCOMPLETE'
result = []
for i, letter in enumerate(letters):
    x, y = i % 4, i // 4
    box = (x * im.width // 4, y * im.height // 4,
           (x + 1) * im.width // 4, (y + 1) * im.height // 4)
    cell = im.crop(box)
    bounds = cell.getchannel('A').point(lambda a: 255 if a > 16 else 0).getbbox()
    if not bounds:
        raise RuntimeError(f'Empty cell {i}')
    glyph = cell.crop(bounds)
    padded = Image.new('RGBA', (glyph.width + 12, glyph.height + 12))
    padded.paste(glyph, (6, 6))
    name = f'{i+1:02d}-{letter}.png'
    padded.save(folder / name)
    result.append({'index': i + 1, 'letter': letter, 'file': name,
                   'width': padded.width, 'height': padded.height})
(root / '.ae-codex/rwd007-13-letter-assets.json').write_text(
    json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({'sheet_size': im.size, 'count': len(result), 'assets': result}))
