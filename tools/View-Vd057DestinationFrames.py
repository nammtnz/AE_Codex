import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
p = root / '.ae-codex/inspection/vd057-destination-hand'
plan = json.loads((root / '.ae-codex/vd057-destination-hand-plan.json').read_text())
labels = ['CLICK', 'HOLD', 'TRAIN ARRIVES', 'BEFORE LEAVING']
expected = [p / f'cue{i}-{j}.png' for i in range(len(plan['cues'])) for j in range(4)]
missing = [str(f) for f in expected if not f.is_file()]
if missing:
    raise RuntimeError(f'{len(missing)} frames still pending')
for page in range(math.ceil(len(plan['cues']) / 4)):
    indices = list(range(page * 4, min(page * 4 + 4, len(plan['cues']))))
    s = Image.new('RGB', (1080, len(indices) * 505))
    d = ImageDraw.Draw(s)
    for row, i in enumerate(indices):
        cue = plan['cues'][i]
        for j in range(4):
            im = Image.open(p / f'cue{i}-{j}.png').convert('RGB').resize((270, 480))
            s.paste(im, (j * 270, row * 505))
            d.text((j * 270 + 2, row * 505 + 481), f'{i} {labels[j]} S{cue["scene"]} T{cue["tile"]}', fill='white')
    s.save(p / f'sheet{page}.png')
print(f'Built {math.ceil(len(plan["cues"]) / 4)} sheets from {len(expected)} AE frames')
