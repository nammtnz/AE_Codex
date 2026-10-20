from pathlib import Path
from PIL import Image,ImageDraw
import json,sys,math
root=Path(sys.argv[1]);rows=json.loads((root/'crossing-proof.json').read_text());pairs=[]
for r in rows:
 key=(r['id'],r['event'])
 if key not in pairs:pairs.append(key)
sheet=Image.new('RGB',(900,len(pairs)*210),'#222');d=ImageDraw.Draw(sheet)
for n,key in enumerate(pairs):
 for col,phase in enumerate(['press','arrival']):
  r=next(r for r in rows if (r['id'],r['event'])==key and r['phase']==phase);im=Image.open(root/r['file']).convert('RGB');x,y=r['x'],r['y'];im=im.crop((x-150,y-110,x+250,y+75)).resize((450,185));sheet.paste(im,(col*450,n*210+25));d.text((col*450+3,n*210+3),f"{r['name']} E{r['event']} {phase} {r['t']:.3f}s",fill='white')
sheet.save(root/'missing-crossings-proof.jpg')
