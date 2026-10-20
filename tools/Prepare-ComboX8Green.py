"""Prepare the IW recolor at the existing AE source's exact canvas size."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageFilter, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets/vd057-praise-3d'
source=ASSETS/'generated/combo-x8-green.png'
old=Image.open(ASSETS/'ready/combo-x8.png').convert('RGBA')
image=Image.open(source).convert('RGBA')
alpha=image.getchannel('A')
if alpha.getextrema() != (0,255):
    raise ValueError('IW output must contain real transparency')
support=alpha.point(lambda a:255 if a>=64 else 0).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.MaxFilter(7))
clean=np.asarray(alpha).copy()
clean[np.asarray(support)==0]=0
image.putalpha(Image.fromarray(clean))
box=image.getchannel('A').getbbox()
target=old.getchannel('A').getbbox()
sprite=image.crop(box).resize((target[2]-target[0],target[3]-target[1]),Image.Resampling.LANCZOS)
final=Image.new('RGBA',old.size)
final.alpha_composite(sprite,(target[0],target[1]))
path=ASSETS/'ready/combo-x8-green.png'
final.save(path)
data={'model':'gpt-image-2.5-sunburst','skill':'iw-imagegen','promptFile':str(ROOT/'.ae-codex/combo-x8-green-edit-prompt.txt'),'file':str(path),'width':final.width,'height':final.height,'alphaExtrema':list(final.getchannel('A').getextrema()),'generatedFile':str(source),'generatedCrop':list(box),'targetBounds':list(target),'oldSourceFile':str(ASSETS/'ready/combo-x8.png')}
(ROOT/'.ae-codex/combo-x8-green-asset.json').write_text(json.dumps(data,indent=2),encoding='utf-8')

# Updated user-facing set preview; the source assets for the other words are untouched.
manifest=json.loads((ROOT/'.ae-codex/vd057-praise-assets.json').read_text(encoding='utf-8-sig'))
preview=Image.new('RGB',(1200,1100),(87,179,62))
draw=ImageDraw.Draw(preview)
for i,row in enumerate(manifest['assets']):
    art=Image.open(path if row['key']=='combo-x8' else row['file']).convert('RGBA')
    art.thumbnail((550,205),Image.Resampling.LANCZOS)
    x,y=(i%2)*600,(i//2)*265
    preview.paste(art,(x+(600-art.width)//2,y+35+(205-art.height)//2),art)
    draw.text((x+24,y+15),row['key'].upper(),fill=(255,255,255))
preview.save(ASSETS/'praise-3d-preview.jpg',quality=95)
print(json.dumps(data,indent=2))
