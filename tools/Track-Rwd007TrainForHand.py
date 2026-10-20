from pathlib import Path
import subprocess,json,math
from PIL import Image,ImageChops
root=Path(__file__).resolve().parents[1]
ff=r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
jobs=[('first',r'E:/Task/Snacky Dash/RWD_VD007/FT/Movie_009.mp4',63.3666667,8.1,1,0),('second',r'E:/Task/Snacky Dash/RWD_VD007/FT/Movie_012.mp4',75.9888889,16.1,.6,12.3666667)]
plan=json.loads((root/'.ae-codex/rwd007-asmr-plan.json').read_text())
tracks={};reports=[]
for name,path,start,dur,ratio,outstart in jobs:
 raw=subprocess.run([ff,'-v','error','-ss',str(start),'-i',path,'-t',str(dur),'-vf','fps=30,scale=270:480','-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
 size=270*480*3;pts=[];prev=None
 for fi,idx in enumerate(range(0,len(raw)-size+1,size)):
  im=Image.frombytes('RGB',(270,480),raw[idx:idx+size]);r,g,b=im.split()
  mask=ImageChops.multiply(ImageChops.multiply(r.point(lambda x:255 if x>228 else 0),g.point(lambda x:255 if x>224 else 0)),b.point(lambda x:255 if x<75 else 0))
  pixels={i for i,v in enumerate(mask.tobytes()) if v}
  candidates=[]
  while pixels:
   seed=pixels.pop();group=[seed];stack=[seed]
   while stack:
    at=stack.pop()
    for n in (at-1,at+1,at-270,at+270):
     if n in pixels:pixels.remove(n);stack.append(n);group.append(n)
   if len(group)<15:continue
   xs=[i%270 for i in group];ys=[i//270 for i in group];w=max(xs)-min(xs)+1;h=max(ys)-min(ys)+1
   if min(w,h)<5 or not .5<w/h<2.0:continue
   x=sum(xs)/len(xs);y=sum(ys)/len(ys)
   candidates.append((x,y,len(group),w,h))
  if not candidates:continue
  if prev:
   candidate=min(candidates,key=lambda p:math.dist(p[:2],prev[:2])-.015*p[2])
  else:candidate=max(candidates,key=lambda p:p[2])
  prev=candidate
  x=(candidate[0]-135)*4.8533333333+540;y=(candidate[1]-240)*4.8533333333+960
  pts.append([outstart+fi/30*ratio,x,y,candidate[2]])
 tracks[name]=pts
 for i,cue in enumerate(plan['cues']):
  if cue[3]!=(1 if name=='first' else 2):continue
  # Match each known route visit within a reasonable expected window.
  expected=plan['previousTimes'][i]
  candidates=[p for p in pts if expected-.30<=p[0]<=expected+1.0]
  point=min(candidates,key=lambda p:math.dist(p[1:3],cue[1:3]))
  reports.append(dict(index=i+1,expected=expected,closest_time=point[0],x=point[1],y=point[2],target=cue[1:3],distance=math.dist(point[1:3],cue[1:3])))
(root/'.ae-codex/rwd007-train-tracking.json').write_text(json.dumps(dict(tracks=tracks,visits=reports),indent=2),encoding='utf-8')
print(json.dumps(reports,indent=2))
