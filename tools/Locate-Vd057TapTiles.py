import json
from pathlib import Path
import numpy as np
from PIL import Image
root=Path(__file__).resolve().parents[1]
for t in [0,6,12,24,36,50]:
 im=np.array(Image.open(root/f'.ae-codex/inspection/vd057-timing/t{t}.png').convert('RGB').resize((360,640)))
 r,g,b=[im[:,:,i].astype(int) for i in range(3)]
 mask=(r>190)&(r<250)&(g>135)&(g<200)&(b>80)&(b<160)&(r-g>35)&(g-b>25)
 pixels=set(np.flatnonzero(mask));boxes=[]
 while pixels:
  seed=pixels.pop();stack=[seed];group=[seed]
  while stack:
   at=stack.pop()
   for n in [at-1,at+1,at-360,at+360]:
    if n in pixels:pixels.remove(n);stack.append(n);group.append(n)
  if len(group)<20:continue
  xs=[x%360 for x in group];ys=[x//360 for x in group];w=max(xs)-min(xs)+1;h=max(ys)-min(ys)+1
  if 5<=w<=16 and 5<=h<=16 and .65<w/h<1.5:boxes.append([round(sum(xs)/len(xs),1),round(sum(ys)/len(ys),1),w,h])
 print(t,boxes)
