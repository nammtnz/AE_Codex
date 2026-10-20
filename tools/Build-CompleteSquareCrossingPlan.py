from pathlib import Path
import json,copy,sys
root=Path(sys.argv[1]);previous=json.loads((root/'direction-square-plan.json').read_text());rows=json.loads((root/'all-crossings-proposed.json').read_text());result=[]
for cid in [13,477,671,811,1059,1132]:
 p=copy.deepcopy(next(p for p in previous if p['id']==cid));p['previousEvents']=copy.deepcopy(p['events']);events=[]
 for r in rows:
  if r['id']!=cid:continue
  t=r['t'];pt=r['point'];arrival=r['arrival']
  if cid==477 and pt==[332,1304]:t=2.925
  if cid==477 and pt==[540,1301]:t=3.05
  if cid in [13,477] and pt==[910,672]:t=20.0 if cid==13 else 7.25
  if cid==477 and pt==[540,959] and arrival==4.5:t=4.2
  if cid==477 and pt==[748,966] and arrival==6.5:t=6.2
  if cid in [1059,1132] and pt==[766,652]:t=4.15
  if cid==1132 and pt==[363,1176] and arrival==8.5:t=8.2
  kind='outlined-square' if pt in [[540,607],[540,1301],[540,959],[328,464],[752,464],[413,930]] else 'solid-square'
  e={'t':t,'point':pt,'arrival':arrival,'kind':kind,'reviewed':True}
  if p['mode']=='projected':e['layer']='ARROW GLYPH FX | lower right'
  events.append(e)
 if cid in [811,1132]:
  source=671 if cid==811 else 1059
  missing=next(r for r in rows if r['id']==source and r['point']==[919,652])
  events.append({'t':missing['t'],'point':missing['point'],'arrival':missing['arrival'],'kind':'solid-square','reviewed':True,'layer':'ARROW GLYPH FX | lower right'})
 p['events']=sorted(events,key=lambda e:e['t']);p['timingNote']='Every visually reviewed locomotive square crossing in sampled gameplay gets a press; includes repeated visits; hand retained at 30%.';result.append(p)
for src,cid,name in [(13,1,'16x9'),(477,496,'16x10')]:
 p=copy.deepcopy(next(p for p in result if p['id']==src));p.update(id=cid,name=name,previousEvents=copy.deepcopy(next(p for p in previous if p['id']==cid)['events']))
 for e in p['events']:e['point']=[960+(e['point'][0]-540)*.5625,e['point'][1]*.5625]
 result.append(p)
for p in result:
 times=[e['t'] for e in p['events']]
 if len(set(times))!=len(times):raise ValueError('Duplicate press time '+p['name'])
(root/'complete-crossing-plan.json').write_text(json.dumps(result,indent=2));print([(p['name'],len(p['events'])) for p in result])
