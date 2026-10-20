from pathlib import Path
from PIL import Image,ImageDraw
import json,sys
root=Path(sys.argv[1]);base=root.parent/'20261012-135005-186972c0';projection={p['id']:p['samples'] for p in json.loads((base/'outline-projection.json').read_text())};ids=[13,1,477,496,671,811,1059,1132];times=[3.84,3.84,.99,.99,22.49,22.49,8.79,8.79];sheet=Image.new('RGB',(1200,560),'#222');draw=ImageDraw.Draw(sheet)
for n,(cid,t) in enumerate(zip(ids,times)):
 im=Image.open(root/f'c{cid}.png').convert('RGB')
 if cid in [13,477]:x,y=540,607
 elif cid in [1,496]:x,y=960,607*.5625
 else:_,x,y=min(projection[cid],key=lambda v:abs(v[0]-t))
 crop=im.crop((x-130,y-110,x+170,y+140));sheet.paste(crop,((n%4)*300,(n//4)*280+30));draw.text(((n%4)*300+5,(n//4)*280+5),f'comp {cid}: outlined square, hand 30%',fill='white')
sheet.save(root/'outlined-small-hand-review.jpg')
plans=json.loads((base/'outline-small-hand-plan.json').read_text())
for p in plans:p.pop('previousEvents',None)
(base/'direction-square-plan.json').write_text(json.dumps(plans,indent=2))
