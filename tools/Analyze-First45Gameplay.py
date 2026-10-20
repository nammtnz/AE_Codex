from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np,json,math
root=Path(r'C:\Users\nguye\AE_Codex\.ae-codex\inspection\source-first45')
points=[[363,1176],[616,462],[160,652],[766,652],[919,652],[616,938],[766,1176],[413,930]]
tracks=[]
for idx,f in enumerate(sorted(root.glob('s*.jpg'))):
 a=np.asarray(Image.open(f).convert('RGB')).astype(float)
 m=(a[:,:,0]>115)&(a[:,:,1]<a[:,:,0]*.60)&(a[:,:,2]<a[:,:,0]*.75)
 m[:175,:]=False;m[825:,:]=False
 ys,xs=np.where(m);pts=set(zip(xs.tolist(),ys.tolist()));groups=[]
 while pts:
  q=[pts.pop()];g=[]
  while q:
   x,y=q.pop();g.append((x,y))
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
    p=(x+dx,y+dy)
    if p in pts:pts.remove(p);q.append(p)
  if len(g)>=5:
   xx,yy=zip(*g);w=max(xx)-min(xx)+1;h=max(yy)-min(yy)+1
   if 3<=w<=35 and 3<=h<=35:groups.append((len(g),sum(xx)/len(g),sum(yy)/len(g),w,h))
 if groups:
  g=max(groups);tracks.append(dict(t=idx/8,x=g[1]*2.026666666667-7.2,y=g[2]*2.026666666667-12.8,file=f.name))
events=[]
for point in points:
 rows=[q for q in tracks if math.hypot(q['x']-point[0],q['y']-point[1])<65]
 groups=[]
 for q in rows:
  if not groups or q['t']-groups[-1][-1]['t']>.40:groups.append([])
  groups[-1].append(q)
 for g in groups:
  q=min(g,key=lambda v:math.hypot(v['x']-point[0],v['y']-point[1]));arrival=q['t']
  if arrival<.5:continue
  events.append(dict(arrival=arrival,t=round(max(.1,arrival-.4),4),point=point,distance=round(math.hypot(q['x']-point[0],q['y']-point[1]),1)))
events.sort(key=lambda q:q['t'])
(root/'first45-hand-plan.json').write_text(json.dumps(dict(events=events,track=tracks),indent=2))
for page in range(math.ceil(len(events)/12)):
 es=events[page*12:(page+1)*12];s=Image.new('RGB',(960,150*len(es)),(22,22,22));d=ImageDraw.Draw(s)
 for j,e in enumerate(es):
  for col,t in enumerate([e['t'],e['arrival']]):
   im=Image.open(root/f"s{round(t*8)+1:04}.jpg");x=(e['point'][0]+7.2)/2.026666666667;y=(e['point'][1]+12.8)/2.026666666667
   im=im.crop((x-85,y-45,x+85,y+45)).resize((450,120));s.paste(im,(col*480,j*150+25));d.text((col*480+4,j*150+3),f"{e['point']} t={t} {'press' if col==0 else 'arrival'} d={e['distance']}",fill='white')
 s.save(root/f'click-review{page+1}.jpg',quality=95)
print('tracked',len(tracks),'events',len(events));print(json.dumps(events))
ts=[26+i*.25 for i in range(16)];s=Image.new('RGB',(1280,900),(22,22,22));d=ImageDraw.Draw(s)
for j,t in enumerate(ts):
 im=Image.open(root/f's{round(t*8)+1:04}.jpg');im=im.crop((120,290,310,510)).resize((300,190));x=j%4*320;y=j//4*225;s.paste(im,(x,y+25));d.text((x+4,y+3),str(t),fill='white')
s.save(root/'green-fill-review.jpg',quality=95)
