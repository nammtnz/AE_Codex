from pathlib import Path
import json,sys,math
from PIL import Image,ImageDraw
root=Path(sys.argv[1]);rows=json.loads((root/'head-candidates.json').read_text())
manual={(13,12):(646,1049),(1059,5):(631,444),(1132,5):(1038,73.5),(1059,7):(554,1145),(1132,7):(970.5,673.5)}
groups={}
for s in rows:groups.setdefault((s['compId'],s['event']),[]).append(s)
plans={};chosen=[]
for key,ss in groups.items():
 ss.sort(key=lambda s:s['time']);mid=ss[2];qs=mid['candidates'];mx,my=manual.get(key,(qs[0]['x'],qs[0]['y']) if qs else (None,None))
 if mx is None:raise ValueError(('No contact',key))
 points=[]
 for s in ss:
  if s is mid:x,y=mx,my
  elif s['candidates']:
   q=s['candidates'][0]
   if key==(13,12):
    q=min(s['candidates'],key=lambda q:abs(q['w']-38)+abs(q['h']-36))
   x,y=q['x'],q['y']
  else:x,y=None,None
  points.append([s['time'],x,y])
 for k,p in enumerate(points):
  if p[1] is not None:continue
  known=[(abs(j-k),j) for j,v in enumerate(points) if v[1] is not None];j=min(known)[1];p[1:]=points[j][1:]
 for s,p in zip(ss,points):chosen.append(dict(s,x=p[1],y=p[2]))
 c=plans.setdefault(mid['compId'],{'id':mid['compId'],'name':mid['compName'],'events':[]});c['events'].append({'t':mid['tap'],'point':[mx,my],'samples':points})
plans=list(plans.values());[c['events'].sort(key=lambda e:e['t']) for c in plans]
by_id={c['id']:c for c in plans}
for wide,portrait in [(1,13),(496,477)]:
 for e,pe in zip(by_id[wide]['events'],by_id[portrait]['events']):
  e['point']=[960+(pe['point'][0]-540)*.5625,pe['point'][1]*.5625]
  e['samples']=[[t,960+(x-540)*.5625,y*.5625] for t,x,y in pe['samples']]
(root/'train-head-plan.json').write_text(json.dumps(plans,indent=2),encoding='utf-8')
for c in plans:
 shots=[s for s in chosen if s['compId']==c['id']];sheet=Image.new('RGB',(1000,220*len(c['events'])),'#222222');d=ImageDraw.Draw(sheet)
 for n,s in enumerate(shots):
  im=Image.open(root/s['file']).convert('RGB');draw=ImageDraw.Draw(im);x,y=s['x'],s['y'];draw.ellipse((x-4,y-4,x+4,y+4),outline='magenta',width=2);radius=70 if c['id'] in [1,496] else 110;im=im.crop((x-radius,y-radius,x+radius,y+radius)).resize((200,195));sheet.paste(im,((n%5)*200,(n//5)*220+25));d.text(((n%5)*200+2,(n//5)*220+2),f"e{s['event']} t{s['time']:.3f}",fill='white')
 sheet.save(root/f'track-review-{c["id"]}.jpg')
print('Plan:',[(c['name'],len(c['events'])) for c in plans])
