import json,subprocess,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1];ff=r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
jobs=[(1,'Movie_015.mp4',15,14.7,[(179.2,147.7),(35.5,241.1),(322.9,241),(250.9,308.8),(322.9,308.9),(322.9,489),(179,556.5)],36.333333),(2,'Movie_025.mp4',54.2666667,50.7,[(30.4,172.6),(122.5,170),(233,170),(122.5,259.4),(233,259.3),(122.5,519.4),(233,519.3)],37.666667)]
alltracks={};visits=[]
out=root/'.ae-codex/inspection/vd057-train-tracking';out.mkdir(exist_ok=True)
for scene,file,start,dur,pts,xoff in jobs:
 raw=subprocess.run([ff,'-v','error','-ss',str(start),'-i','E:/Task/Snacky Dash/RWD_VD007/FT/'+file,'-t',str(dur),'-vf','fps=10,scale=180:320','-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
 frames=np.frombuffer(raw,dtype='uint8').reshape(-1,320,180,3);track=[];prev=None;debug=[]
 for n,frame in enumerate(frames):
  im=frame.astype(int);r,g,b=[im[:,:,i] for i in range(3)];mask=(r>145)&(g<85)&(b<85)&(r-g>70)&(r>b*1.5);mask[:80,:]=False;mask[275:,:]=False;mask[:,:14]=False;mask[:,166:]=False
  pix=set(np.flatnonzero(mask));candidates=[]
  while pix:
   seed=pix.pop();stack=[seed];group=[seed]
   while stack:
    at=stack.pop()
    for j in (at-1,at+1,at-180,at+180):
     if j in pix:pix.remove(j);stack.append(j);group.append(j)
   if not 2<=len(group)<=70:continue
   xs=[a%180 for a in group];ys=[a//180 for a in group];candidates.append((sum(xs)/len(xs),sum(ys)/len(ys),len(group)))
  if candidates:
   cand=max(candidates,key=lambda a:a[2]-(0 if prev is None else min(math.dist(a[:2],prev[:2]),25)*.12));prev=cand;track.append(dict(raw=round(start+n/10,4),point=[cand[0]*8,cand[1]*8],screen=[cand[0]*2.4-xoff,cand[1]*2.4-64],pixels=cand[2]))
  if n%max(1,len(frames)//30)==0:
   image=Image.fromarray(frame);d=ImageDraw.Draw(image)
   if candidates:d.ellipse((cand[0]-5,cand[1]-5,cand[0]+5,cand[1]+5),outline='white',width=1)
   debug.append((start+n/10,image))
 alltracks[str(scene)]=track
 for k,pt in enumerate(pts):
  hits=[a for a in track if math.dist(a['screen'],pt)<30];groups=[]
  for a in hits:
   if not groups or a['raw']-groups[-1][-1]['raw']>.35:groups.append([])
   groups[-1].append(a)
  for group in groups:
   best=min(group,key=lambda a:math.dist(a['screen'],pt));entry=group[0]['raw'];
   if math.dist(best['screen'],pt)>20:continue
   visits.append(dict(scene=scene,tile=k,raw=entry,closestRaw=best['raw'],distance=round(math.dist(best['screen'],pt),2),point=[pt[0]*3,pt[1]*3],frames=len(group)))
 sheet=Image.new('RGB',(180*10,345*3));d=ImageDraw.Draw(sheet)
 for i,(t,im) in enumerate(debug[:30]):sheet.paste(im,(i%10*180,i//10*345));d.text((i%10*180,i//10*345+320),f'{t:.2f}',fill='white')
 sheet.save(out/f'scene{scene}.png')
visits.sort(key=lambda a:(a['scene'],a['raw']));(root/'.ae-codex/vd057-train-contact-tracks.json').write_text(json.dumps(dict(tracks=alltracks,visits=visits),indent=2));print(json.dumps(visits,indent=2))
