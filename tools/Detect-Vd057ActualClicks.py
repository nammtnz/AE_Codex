import json,subprocess,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1];ff=r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
# Measured switch centers in the 360x640 composition view, separate from direction signs.
jobs=[(1,'Movie_015.mp4',15.0,14.7,[(179.2,147.7),(35.5,241.1),(322.9,241),(250.9,308.8),(322.9,308.9),(322.9,489),(179,556.5)],36.333333),(2,'Movie_025.mp4',54.2666667,50.7,[(30.4,172.6),(122.5,170),(233,170),(122.5,259.4),(233,259.3),(122.5,519.4),(233,519.3)],37.666667)]
all_events=[];results=[]
for scene,file,start,dur,pts,xoff in jobs:
 centers=[((x+xoff)/1.2,(y+64)/1.2) for x,y in pts];labels=''.join(f'[s{i}]' for i in range(len(pts)))
 filters=[f'[0:v]fps=30,scale=360:640,split={len(pts)}{labels}']
 for i,(x,y) in enumerate(centers):filters.append(f'[s{i}]crop=12:12:{round(x)-6}:{round(y)-6}[c{i}]')
 filters.append(''.join(f'[c{i}]' for i in range(len(pts)))+f'hstack=inputs={len(pts)}[out]')
 raw=subprocess.run([ff,'-v','error','-ss',str(start),'-i','E:/Task/Snacky Dash/RWD_VD007/FT/'+file,'-t',str(dur),'-filter_complex',';'.join(filters),'-map','[out]','-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
 frames=np.frombuffer(raw,dtype='uint8').reshape(-1,12,12*len(pts),3);states=[]
 for k in range(len(pts)):
  f=frames[:,:,k*12:k*12+12,:].astype(int);r,g,b=[f[:,:,:,i] for i in range(3)];beige=(r>175)&(r<255)&(g>115)&(g<205)&(b>60)&(b<165)&(r-g>30)&(g-b>18);gray=(r>55)&(r<130)&(g>65)&(g<145)&(b>65)&(b<155)&(abs(r-g)<25)&(abs(g-b)<25)
  bi=beige[:,4:8,4:8].mean((1,2));gi=gray[:,4:8,4:8].mean((1,2));edge=beige.sum((1,2));st=np.where(bi>.45,1,np.where((gi>.65)&(edge>4),0,-1));last=None;candidate=None;run=0;events=[]
  for n,s in enumerate(st):
   if s<0:candidate=None;run=0;continue
   if s==candidate:run+=1
   else:candidate=s;run=1
   if run==3:
    if last is not None and s!=last:
     at=start+(n-2)/30;events.append(dict(scene=scene,tile=k,raw=round(at,4),state=int(s),point=[pts[k][0]*3,pts[k][1]*3]));all_events.append(events[-1])
    last=s
  results.append(dict(scene=scene,tile=k,point=pts[k],events=events,valid=float((st>=0).mean())))
  sheet=Image.new('RGB',(12*len(pts)*4,12*4*min(30,len(frames))));
 for n in range(min(30,len(frames))):sheet.paste(Image.fromarray(frames[n*max(1,len(frames)//30)]).resize((12*len(pts)*4,48)),(0,n*48))
 out=root/'.ae-codex/inspection/vd057-switch-detection';out.mkdir(exist_ok=True);sheet.save(out/f'scene{scene}-samples.png')
report=dict(tiles=results,events=sorted(all_events,key=lambda e:(e['scene'],e['raw'])))
(root/'.ae-codex/vd057-actual-switch-events.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
