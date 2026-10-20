import sys
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
run = sys.argv[1]
if not run.replace('-', '').isalnum():
    raise ValueError('Run ID')
folder = root / '.ae-codex/inspection' / run
labels = ['Before win', 'LEVEL pops', 'LEVEL holds', 'COMPLETE pops', 'Both + 3 stars', 'Hold / shine', 'Outro']
for name, ids, width, height in [('landscape', [811, 1132], 274, 154), ('portrait', [671, 1059], 180, 320)]:
    sheet = Image.new('RGB', (7 * width, 2 * (height + 30)), '#1b1f25')
    draw = ImageDraw.Draw(sheet)
    for row, comp_id in enumerate(ids):
        for stage in range(7):
            path = folder / f'c{comp_id}-stage{stage}.png'
            with Image.open(path) as source:
                frame = source.convert('RGB').resize((width, height), Image.Resampling.LANCZOS)
            x, y = stage * width, row * (height + 30)
            draw.text((x+4, y+4), f'{comp_id}: {labels[stage]}', fill='white')
            sheet.paste(frame, (x, y+25))
    sheet.save(folder / f'review-{name}.jpg', quality=94)

preview = Image.new('RGB', (1440, 438), '#1b1f25')
draw = ImageDraw.Draw(preview)
for column, stage in enumerate([1, 4]):
    with Image.open(folder / f'c811-stage{stage}.png') as source:
        frame = source.convert('RGB').resize((720, 405), Image.Resampling.LANCZOS)
    draw.text((column*720+12, 8), ['1. LEVEL popup', '2. COMPLETE popup - retain both words'][column], fill='white')
    preview.paste(frame, (column*720, 30))
preview.save(folder / 'preview-sequential-words.jpg', quality=94)
print(folder)
