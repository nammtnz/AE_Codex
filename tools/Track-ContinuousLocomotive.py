"""Build a reviewable gameplay locomotive track from captured frames."""
from pathlib import Path
import json,sys,math
import numpy as np
from PIL import Image,ImageDraw
root=Path(sys.argv[1]);manifest=root/'continuous-samples.json'
if manifest.exists():samples=json.loads(manifest.read_text(encoding='utf-8-sig'))
else:
 samples=[];targets={13:('9x16',27.0333333333333),477:('9x17',12),671:('9x16-',27),1059:('9x16- 2',12),811:('16x9-',27),1132:('16x9- 2',12)}
 for cid,(name,end) in targets.items():
  files=list(root.glob(f'c{cid}-f*.png'))
  if len(files)<math.ceil(end*8):continue
  for k in range(math.ceil(end*8)):
   samples.append({'compId':cid,'name':name,'time':min(k/8,end-1/30),'end':end,'file':f'c{cid}-f{k}.png'})
anchors=json.loads((root.parent/'20261012-114557-ee6746db'/'train-head-plan.json').read_text())
def locate(path):
 im=Image.open(path).convert('RGB');factor=2;a=np.asarray(im.resize((im.width//factor,im.height//factor)))
 r,g,b=[a[:,:,i].astype(int) for i in range(3)];mask=(r>195)&(g>160)&(b<110)&(r-g<75)
 seen=np.zeros(mask.shape,dtype=bool);out=[]
 for y,x in zip(*np.nonzero(mask)):
  if seen[y,x]:continue
  stack=[(y,x)];seen[y,x]=True;points=[]
  while stack:
   cy,cx=stack.pop();points.append((cy,cx))
   for ny,nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
    if 0<=ny<mask.shape[0] and 0<=nx<mask.shape[1] and mask[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;stack.append((ny,nx))
  if len(points)<7:continue
  ys,xs=zip(*points);x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys);w=x1-x0+1;h=y1-y0+1
  if not .65<w/h<1.65 or len(points)/(w*h)<.48:continue
  pad=max(w,h);xa=max(0,x0-pad);xb=min(a.shape[1],x1+pad+1);ya=max(0,y0-pad);yb=min(a.shape[0],y1+pad+1)
  rr=r[ya:yb,xa:xb];gg=g[ya:yb,xa:xb];bb=b[ya:yb,xa:xb]
  red=(rr>140)&(gg<150)&(rr>gg*1.4)&(rr>bb*1.15);blue=(bb>115)&(bb>rr*1.3)&(gg>60)
  score=min(red.sum()/(w*h),2)*min(blue.sum()/(w*h),2)*len(points)
  if score<.3:continue
  ry,rx=np.nonzero(red);cx=(x0+x1)/2;cy=(y0+y1)/2
  # Average red boiler position gives the locomotive's facing direction.
  dx=float(rx.mean()+xa-cx);dy=float(ry.mean()+ya-cy)
  # The red circular boiler with a dark centre distinguishes the engine
  # from square yellow direction-button pedestals and orange wagons.
  dark=(rr<125)&(gg<120)&(bb<150);dyc,dxc=np.nonzero(dark);best_ring=0;boiler=None
  if len(dxc):
   dist=np.hypot(dxc+xa-cx,dyc+ya-cy);valid=(dist>max(w,h)*.45)&(dist<max(w,h)*1.45);dxc=dxc[valid][::2];dyc=dyc[valid][::2]
   if len(dxc):
    scores=np.zeros(len(dxc));radius=max(2,max(w,h)*.23)
    for angle in np.linspace(0,2*np.pi,12,endpoint=False):
     xx=np.clip(np.rint(dxc+math.cos(angle)*radius).astype(int),0,rr.shape[1]-1);yy=np.clip(np.rint(dyc+math.sin(angle)*radius).astype(int),0,rr.shape[0]-1);scores+=red[yy,xx]
    bi=int(scores.argmax());best_ring=float(scores[bi]/12);boiler=(float(dxc[bi]+xa-cx),float(dyc[bi]+ya-cy))
  score=score*.15+best_ring**4*200
  if best_ring>.5:dx,dy=boiler
  direction=0 if abs(dx)+abs(dy)<max(w,h)*.15 else (1 if abs(dx)>abs(dy) and dx>0 else 3 if abs(dx)>abs(dy) else 2 if dy>0 else 4)
  out.append({'x':float(cx*factor),'y':float(cy*factor),'w':int(w*factor),'h':int(h*factor),'score':float(score),'dir':direction,'ring':best_ring})
 redmask=(r>145)&(g<130)&(r>g*1.5)&(r>b*1.2);seen=np.zeros(redmask.shape,dtype=bool)
 for y,x in zip(*np.nonzero(redmask)):
  if seen[y,x]:continue
  stack=[(y,x)];seen[y,x]=True;pts=[]
  while stack:
   cy,cx=stack.pop();pts.append((cy,cx))
   for ny,nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
    if 0<=ny<redmask.shape[0] and 0<=nx<redmask.shape[1] and redmask[ny,nx] and not seen[ny,nx]:seen[ny,nx]=True;stack.append((ny,nx))
  if len(pts)<7:continue
  ys,xs=zip(*pts);x0,x1=min(xs),max(xs);y0,y1=min(ys),max(ys);w=x1-x0+1;h=y1-y0+1;cx=(x0+x1)/2;cy=(y0+y1)/2;diam=(w+h)/2
  if not .75<w/h<1.35 or len(pts)/(w*h)<.28:continue
  iy=int(cy);ix=int(cx)
  if not (r[iy,ix]<150 and g[iy,ix]<140 and b[iy,ix]<160):continue
  best=0;point=None;direction=0
  for ang in np.linspace(0,2*np.pi,8,endpoint=False):
   dx=math.cos(ang);dy=math.sin(ang);px=cx+dx*diam*1.18;py=cy+dy*diam*1.18;half=max(3,diam*.65)
   xa=max(0,int(px-half));xb=min(mask.shape[1],int(px+half+1));ya=max(0,int(py-half));yb=min(mask.shape[0],int(py+half+1))
   if xb<=xa or yb<=ya:continue
   mm=mask[ya:yb,xa:xb];fraction=mm.sum()/max(1,mm.size)
   if fraction>best:
    best=float(fraction);point=(px*factor,py*factor);direction=3 if abs(dx)>abs(dy) and dx>0 else 1 if abs(dx)>abs(dy) else 4 if dy>0 else 2
  if best>.22:out.append({'x':float(point[0]),'y':float(point[1]),'w':int(diam*factor*1.65),'h':int(diam*factor*1.65),'score':300+best*100,'dir':direction,'ring':1,'boiler':True})
 out.sort(key=lambda q:q['score'],reverse=True);return out[:10]

cache=root/'continuous-candidates-ring-roof.json'
cached={s['file']:s for s in json.loads(cache.read_text())} if cache.exists() else {}
rows=[]
for s in samples:
 if s['file'] in cached:rows.append(cached[s['file']]);continue
 s=dict(s);s['candidates']=locate(root/s['file']);rows.append(s)
cache.write_text(json.dumps(rows),encoding='utf-8')
plans=[];missing=[]
for cid in dict.fromkeys(s['compId'] for s in rows):
 ss=[s for s in rows if s['compId']==cid];anchor=next(c for c in anchors if c['id']==cid)
 nonempty=[(i,s) for i,s in enumerate(ss) if s['candidates']];costs=[];backs=[]
 for k,(i,s) in enumerate(nonempty):
  aa=min(anchor['events'],key=lambda e:abs(e['t']-s['time']));now=[];back=[]
  for q in s['candidates']:
   unary=-math.log(1+q['score'])+.5*abs(math.log(q['w']/q['h']))
   if abs(aa['t']-s['time'])<.08:unary+=math.hypot(q['x']-aa['point'][0],q['y']-aa['point'][1])/max(15,q['w'])*3
   if k:
    pi,ps=nonempty[k-1];options=[]
    for j,pq in enumerate(ps['candidates']):
     distance=math.hypot(q['x']-pq['x'],q['y']-pq['y']);size=max(q['w'],pq['w'],20)
     transition=min(10,distance/size)*.55+abs(math.log(max(1,q['w'])/max(1,pq['w'])))*.7
     options.append(costs[-1][j]+transition)
    best=min(range(len(options)),key=options.__getitem__);now.append(unary+options[best]);back.append(best)
   else:now.append(unary);back.append(0)
  costs.append(now);backs.append(back)
 chosen={};j=min(range(len(costs[-1])),key=costs[-1].__getitem__)
 for k in range(len(nonempty)-1,-1,-1):
  i,s=nonempty[k];chosen[i]=s['candidates'][j];j=backs[k][j]
 track=[]
 for i,s in enumerate(ss):
  if i not in chosen:
   missing.append(s['file']);left=max((k for k in chosen if k<i),default=min(chosen));right=min((k for k in chosen if k>i),default=max(chosen));a=chosen[left];b=chosen[right];u=0 if left==right else (i-left)/(right-left);q=dict(a);q['x']=a['x']+(b['x']-a['x'])*u;q['y']=a['y']+(b['y']-a['y'])*u
  else:q=chosen[i]
  track.append({'t':s['time'],'x':q['x'],'y':q['y'],'w':q['w'],'dir':q['dir'],'file':s['file'],'estimated':i not in chosen})
 # Require facing direction to persist; click when it changes.
 stable=[]
 for i,q in enumerate(track):
  values=[v['dir'] for v in track[max(0,i-1):min(len(track),i+2)] if v['dir']]
  stable.append(max(set(values),key=values.count) if values else 0)
 presses=[];prev=stable[0]
 for i in range(2,len(track)-2):
  current=stable[i]
  if current and current!=prev and stable[i+1]==current and stable[i+2]==current:
   t=max(0,track[i]['t']-.10)
   if (not presses or t-presses[-1]>.4) and t<ss[0]['end']-.2:presses.append(round(t,4))
   prev=current
 plans.append({'id':cid,'name':ss[0]['name'],'end':ss[0]['end'],'track':track,'presses':presses})
 (root/f'track-{cid}.json').write_text(json.dumps(track),encoding='utf-8')
 # Crop every half second for visual review; magenta marks proposed contact.
 frames=track[::4];sheet=Image.new('RGB',(1200,math.ceil(len(frames)/8)*170),'#222222');d=ImageDraw.Draw(sheet)
 for n,q in enumerate(frames):
  im=Image.open(root/q['file']).convert('RGB');draw=ImageDraw.Draw(im);x,y=q['x'],q['y'];draw.ellipse((x-4,y-4,x+4,y+4),outline='magenta',width=2);radius=max(36,int(q['w']*1.2));im=im.crop((x-radius,y-radius,x+radius,y+radius)).resize((150,145));sheet.paste(im,((n%8)*150,(n//8)*170+25));d.text(((n%8)*150+3,(n//8)*170+3),str(q['t'])+(' EST' if q['estimated'] else ''),fill='white')
 sheet.save(root/f'continuous-review-{cid}.jpg')
(root/'continuous-plan.json').write_text(json.dumps(plans,indent=2),encoding='utf-8')
print(json.dumps({'tracks':[(p['name'],len(p['track']),p['presses']) for p in plans],'estimated':missing}))
