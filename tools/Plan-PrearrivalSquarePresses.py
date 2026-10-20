from pathlib import Path
from PIL import Image,ImageDraw
import json,math,sys
root=Path(sys.argv[1]);plans=json.loads((root/'direction-square-plan.json').read_text());windows=json.loads((root/'square-arrival-targets.json').read_text());tracks={p['id']:p['track'] for p in json.loads((root/'continuous-plan.json').read_text())};out=[]
for win in windows:
 p=next(p for p in plans if p['id']==win['id']);e=p['events'][win['event']];choices=[]
 for t,x,y in win['samples']:
  q=min(tracks[p['id']],key=lambda q:abs(q['t']-t));dx,dy={1:(1,0),2:(0,1),3:(-1,0),4:(0,-1),0:(0,0)}[q['dir']];fx=q['x']+dx*q['w']*.65;fy=q['y']+dy*q['w']*.65;dist=math.hypot(fx-x,fy-y)/max(q['w'],15)
  choices.append((dist+.06*abs(t-e['t']-.3),dist,t,x,y,q['w']))
 best=min(choices);arrival=best[2];click=round(max(.033333,arrival-.5),4)
 out.append({'id':p['id'],'event':win['event'],'old':e['t'],'arrival':arrival,'click':click,'distanceWidths':round(best[1],2),'point':[best[3],best[4]],'w':best[5]})
for cid in dict.fromkeys(v['id'] for v in out):
 ss=[v for v in out if v['id']==cid];sheet=Image.new('RGB',(960,len(ss)*205),'#222');d=ImageDraw.Draw(sheet)
 for n,s in enumerate(ss):
  win=next(v for v in windows if v['id']==cid and v['event']==s['event'])
  for col,t in enumerate([s['click'],s['arrival'],s['arrival']+.125]):
   k=round(t*8);file=root/f'c{cid}-f{k}.png'
   if not file.exists():continue
   _,x,y=min(win['samples'],key=lambda v:abs(v[0]-k/8));im=Image.open(file).convert('RGB');dr=ImageDraw.Draw(im);dr.ellipse((x-6,y-6,x+6,y+6),outline='magenta',width=3);rad=max(95,int(s['w']*2));im=im.crop((x-rad,y-rad,x+rad,y+rad)).resize((320,180));sheet.paste(im,(col*320,n*205+25));d.text((col*320+3,n*205+3),f"E{s['event']} {k/8}s {'CLICK' if col==0 else 'ARRIVE'} d={s['distanceWidths']}",fill='white')
 sheet.save(root/f'prearrival-review-{cid}.jpg')
(root/'prearrival-proposed.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
