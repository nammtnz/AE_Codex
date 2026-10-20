from pathlib import Path
import json,math,sys
root=Path(sys.argv[1]);old=json.loads((root/'continuous-plan.json').read_text())
originals=[]
square_sets={0:[[540,1475]],1:[[332,624],[748,624],[748,380],[332,966],[748,966],[332,1304],[748,1304],[332,1540]],2:[[540,473],[328,920],[328,1070],[168,672],[168,1430],[910,1430],[750,1070],[750,920],[910,672],[540,1610]]}
for cid in [13,477]:
 p=next(p for p in old if p['id']==cid);events=[]
 for t in p['presses']:
  q=min(p['track'],key=lambda q:abs(q['t']-t));level=0 if t<(9.7 if cid==13 else 2.9) else 1 if t<(19.8 if cid==13 else 7.1) else 2
  points=square_sets[level];pt=min(points,key=lambda pt:math.hypot(q['x']-pt[0],q['y']-pt[1]));distance=math.hypot(q['x']-pt[0],q['y']-pt[1])
  if distance<230 and (not events or t-events[-1]['t']>.6):events.append({'t':t,'point':pt,'level':level,'distance':round(distance)})
 if cid==477:events=[{'t':.35,'point':[540,1475],'level':0},{'t':3.3,'point':[332,1304],'level':1}]+events
 else:events.append({'t':10.2,'point':[332,1304],'level':1});events.append({'t':24.9,'point':[328,920],'level':2})
 for e in events:
  if e['level']==2 and e['point']==[910,672]:e['point']=[540,473]
 events.sort(key=lambda e:e['t'])
 if not events:raise Exception('No events')
 originals.append({'id':cid,'name':p['name'],'end':p['end'],'mode':'static','events':events})
for src,cid,name in [(13,1,'16x9'),(477,496,'16x10')]:
 p=next(p for p in originals if p['id']==src);e=[dict(e,point=[960+(e['point'][0]-540)*.5625,e['point'][1]*.5625]) for e in p['events']];originals.append(dict(p,id=cid,name=name,events=e))
pts={'lower right':[363,1176],'top junction':[616,462],'left up-down':[160,652],'middle up-down':[766,652],'right down-up':[919,652],'return junction':[616,938],'gate':[766,1176]}
long=[(.50,'lower right'),(3.9,'return junction'),(7.15,'gate'),(9.4,'left up-down'),(11.35,'middle up-down'),(12.55,'right down-up'),(13.85,'top junction'),(15.35,'return junction'),(20.4,'gate'),(22.75,'return junction')]
short=[(.40,'lower right'),(1.8,'return junction'),(2.6,'gate'),(3.8,'left up-down'),(4.45,'middle up-down'),(4.90,'right down-up'),(5.30,'top junction'),(5.9,'return junction'),(7.7,'gate'),(9.0,'return junction')]
for cid in [671,811,1059,1132]:
 p=next(p for p in old if p['id']==cid);originals.append({'id':cid,'name':p['name'],'end':p['end'],'mode':'projected','events':[{'t':t,'point':pts[label],'layer':'ARROW GLYPH FX | '+(label if label!='gate' else 'lower right'),'label':label} for t,label in (short if cid in [1059,1132] else long)],'squares':list(pts.values())})
(root/'direction-square-plan.json').write_text(json.dumps(originals,indent=2))
print(json.dumps(originals,ensure_ascii=False))
