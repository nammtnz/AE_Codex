import json
import math
from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
p = root / '.ae-codex/inspection/vd057-full-route-hand'
plan = json.loads((root / '.ae-codex/vd057-full-route-hand-plan.json').read_text())
expected=[p/f'cue{i}-{j}.png' for i in range(len(plan['cues'])) for j in range(2)]
missing=[str(x) for x in expected if not x.is_file()]
if missing:
    raise RuntimeError(f'{len(missing)} frames pending')
for page in range(math.ceil(len(plan['cues']) / 8)):
    indices=list(range(page*8,min(page*8+8,len(plan['cues']))))
    rows=(len(indices)+1)//2
    sheet=Image.new('RGB',(1080,rows*510));d=ImageDraw.Draw(sheet)
    for slot,i in enumerate(indices):
        cue=plan['cues'][i]
        for j in range(2):
            x=(slot%2*2+j)*270;y=slot//2*510
            sheet.paste(Image.open(p/f'cue{i}-{j}.png').convert('RGB').resize((270,480)),(x,y))
            t=cue['time'] if j==0 else cue['arrival']
            label='CLICK' if j==0 else 'TRAIN ARRIVES'
            d.text((x+2,y+481),f'{i} {label} {t:.3f}',fill='white')
            d.text((x+2,y+494),str(cue['tile'])[:30],fill='yellow' if cue['intermediate'] else 'white')
    sheet.save(p/f'sheet{page}.png')
print(f'{len(expected)} AE frames, {math.ceil(len(plan["cues"])/8)} sheets')
