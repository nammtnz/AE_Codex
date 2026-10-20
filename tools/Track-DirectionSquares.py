from pathlib import Path
import json,math,sys
import numpy as np
from PIL import Image,ImageDraw
root=Path(sys.argv[1])
samples=json.loads((root/'continuous-samples.json').read_text(encoding='utf-8-sig'))
samples=[s for s in samples if int(s['file'].split('-f')[1].split('.')[0])%4==0]
def locate(path):
 im=Image.open(path).convert('RGB');a=np.asarray(im.resize((im.width//2,im.height//2)));r,g,b=[a[:,:,i].astype(float) for i in range(3)];r=np.maximum(r,1)
 mask=(r>165)&(r<238)&(g/r>.72)&(g/r<.84)&(b/r>.46)&(b/r<.66)&(r-g>26)&(g-b>27)
 seen=np.zeros(mask.shape,bool);out=[]
 for y,x in zip(*np.nonzero(mask)):
  if seen[y,x]:continue
  stack=[(y,x)];seen[y,x]=True;pts=[]
  while stack:
   cy,cx=stack.pop();pts.append((cy,cx))
   for ny,nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
    if 0<=ny<mask.shape[0] and 0<=nx<mask.shape[1] and mask[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;stack.append((ny,nx))
  if len(pts)<8:continue
  ys,xs=zip(*pts);x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys);w=x1-x0+1;h=y1-y0+1
  if not .82<w/h<1.18 or not .70<len(pts)/(w*h)<.995 or w<4:continue
  out.append({'x':float(x0+x1),'y':float(y0+y1),'w':int(w*2),'h':int(h*2),'fill':float(len(pts)/(w*h))})
 return out
cache=root/'direction-square-candidates.json'
rows=json.loads(cache.read_text()) if cache.exists() else []
if not rows:
 for s in samples:
  q=dict(s);q['squares']=locate(root/s['file']);rows.append(q)
 cache.write_text(json.dumps(rows))
for cid in dict.fromkeys(s['compId'] for s in rows):
 ss=[s for s in rows if s['compId']==cid];frames=ss[::2];sheet=Image.new('RGB',(1440,math.ceil(len(frames)/6)*350),'#222');d=ImageDraw.Draw(sheet)
 for n,s in enumerate(frames):
  im=Image.open(root/s['file']).convert('RGB');dr=ImageDraw.Draw(im)
  for k,q in enumerate(s['squares']):
   x,y,w=q['x'],q['y'],q['w'];dr.rectangle((x-w/2-4,y-w/2-4,x+w/2+4,y+w/2+4),outline='magenta',width=4);dr.text((x,y),str(k),fill='red',stroke_width=1)
  im.thumbnail((240,325));sheet.paste(im,((n%6)*240,(n//6)*350+25));d.text(((n%6)*240,(n//6)*350),f"{s['time']}s {len(s['squares'])}",fill='white')
 sheet.save(root/f'squares-review-{cid}.jpg')
print(json.dumps({'frames':len(rows),'counts':{cid:sum(bool(s['squares']) for s in rows if s['compId']==cid) for cid in dict.fromkeys(s['compId'] for s in rows)}}))
