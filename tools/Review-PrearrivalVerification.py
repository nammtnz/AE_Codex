from pathlib import Path
from PIL import Image,ImageDraw
import json,sys
root=Path(sys.argv[1]);rows=json.loads((root/'prearrival-verification.json').read_text());base=root.parent/'20261012-135005-186972c0';plans=json.loads((base/'prearrival-reviewed-plan.json').read_text());wins=json.loads((base/'square-arrival-targets.json').read_text());sheet=Image.new('RGB',(1000,8*280),'#222');draw=ImageDraw.Draw(sheet)
for i,p in enumerate(plans):
 sel=1 if p['mode']=='static' else 4;e=p['events'][sel]
 for phase in ['press','arrival']:
  s=next(s for s in rows if s['id']==p['id'] and s['phase']==phase);im=Image.open(root/s['file']).convert('RGB')
  if p['mode']=='static':x,y=e['point']
  else:
   win=next(w for w in wins if w['id']==p['id'] and w['event']==4);_,x,y=min(win['samples'],key=lambda v:abs(v[0]-s['t']))
  crop=im.crop((x-200,y-110,x+250,y+140)).resize((500,250));col=0 if phase=='press' else 1;sheet.paste(crop,(col*500,i*280+30));draw.text((col*500+5,i*280+5),f"{p['name']} {phase} {s['t']:.2f}s",fill='white')
sheet.save(root/'press-before-arrival.jpg')
# Publish current plan only after the bridge confirmed successful mutation.
for p in plans:p.pop('previousEvents',None)
(base/'direction-square-plan.json').write_text(json.dumps(plans,indent=2))
