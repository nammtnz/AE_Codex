from pathlib import Path
from PIL import Image,ImageDraw
import json,sys,math
root=Path(sys.argv[1]);plans=json.loads((root/'direction-square-plan.json').read_text());tracks={p['id']:p['track'] for p in json.loads((root/'continuous-plan.json').read_text())};projections=json.loads((root/'all-choice-projections.json').read_text());rows=[]
static=[([[540,1475],[540,607]],0,9.7),([[332,624],[748,624],[748,380],[332,966],[748,966],[332,1304],[748,1304],[332,1540],[540,959],[540,1301]],9.7,19.8),([[540,473],[328,920],[328,1070],[168,672],[168,1430],[910,1430],[750,1070],[750,920],[910,672],[540,1610],[328,464],[752,464]],19.8,27.03)]
for cid in [13,477,671,811,1059,1132]:
 square_paths=[]
 if cid in [13,477]:
  for level,(pts,start,end) in enumerate(static):
   if cid==477:start,end=[(0,2.9),(2.9,7.1),(7.1,12)][level]
   for point in pts:square_paths.append((point,[[q['t'],*point] for q in tracks[cid] if start<=q['t']<end]))
 else:square_paths=[(p['point'],p['samples']) for p in projections if p['id']==cid]
 events=[]
 for point,ss in square_paths:
  proximity=[]
  for t,x,y in ss:
   q=min(tracks[cid],key=lambda v:abs(v['t']-t));dx,dy={1:(1,0),2:(0,1),3:(-1,0),4:(0,-1),0:(0,0)}[q['dir']];fx=q['x']+dx*q['w']*.5;fy=q['y']+dy*q['w']*.5;dist=math.hypot(fx-x,fy-y)/max(q['w'],15)
   if dist<1.05:proximity.append((t,dist,x,y))
  groups=[]
  for row in proximity:
   if not groups or row[0]-groups[-1][-1][0]>.26:groups.append([])
   groups[-1].append(row)
  for group in groups:
   first=group[0];arrival=first[0];click=round(max(.0333,arrival-.40),4)
   # A scene change must precede the click for static composited levels.
   if cid in [13,477]:click=max(click,ss[0][0]+.05)
   if arrival<.125:continue
   def at(t):return min(ss,key=lambda v:abs(v[0]-t))
   _,x,y=at(click);width,height=(1920,1080) if cid in [811,1132] else (1080,1920)
   while (x<28 or x>width-28 or y<28 or y>height-50) and click<arrival-.1:
    click=round(click+.05,4);_,x,y=at(click)
   visible=28<=x<=width-28 and 28<=y<=height-50
   events.append({'id':cid,'point':point,'arrival':arrival,'t':click,'endNear':group[-1][0],'visible':visible,'samples':ss,'distance':round(first[1],2)})
 events.sort(key=lambda e:e['arrival']);rows+=events
 for page in range(math.ceil(len(events)/10)):
  subset=events[page*10:(page+1)*10];sheet=Image.new('RGB',(900,len(subset)*170),'#222');d=ImageDraw.Draw(sheet)
  for n,e in enumerate(subset):
   for col,t in enumerate([e['t'],e['arrival'],min(e['arrival']+.25,e['samples'][-1][0])]):
    k=round(t*8);f=root/f'c{cid}-f{k}.png'
    if not f.exists():continue
    _,x,y=min(e['samples'],key=lambda v:abs(v[0]-t));im=Image.open(f).convert('RGB');dr=ImageDraw.Draw(im);dr.ellipse((x-6,y-6,x+6,y+6),outline='magenta',width=3);q=min(tracks[cid],key=lambda v:abs(v['t']-t));rad=max(95,int(q['w']*1.8));im=im.crop((x-rad,y-rad*.5,x+rad,y+rad*.5)).resize((300,145));sheet.paste(im,(col*300,n*170+25));d.text((col*300+3,n*170+3),f"E{page*10+n} {e['point']} {t:.2f}s {'PRESS' if col==0 else 'ARRIVE'}",fill='white')
  sheet.save(root/f'audit-crossings-{cid}-{page}.jpg')
 print(cid,[(i,e['point'],e['t'],e['arrival'],e['visible']) for i,e in enumerate(events)])
for e in rows:e.pop('samples')
(root/'all-crossings-proposed.json').write_text(json.dumps(rows,indent=2))
