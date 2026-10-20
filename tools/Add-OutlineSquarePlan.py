from pathlib import Path
import json,copy,sys
root=Path(sys.argv[1]);plans=json.loads((root/'direction-square-plan.json').read_text())
adds={13:[(.15,[540,607]),(3.80,[540,607]),(10.15,[540,1301]),(13.50,[540,959]),(18.65,[540,959]),(20.20,[752,464]),(24.10,[328,464])],477:[(.05,[540,607]),(.95,[540,607]),(3.05,[540,1301]),(4.20,[540,959]),(6.50,[540,959]),(7.50,[752,464]),(9.15,[328,464])]}
for p in plans:
 p['previousEvents']=copy.deepcopy(p['events'])
 if p['mode']=='static':
  src=13 if p['id'] in [13,1] else 477
  for e in p['events']:
   if abs(e['t']-(20.1 if src==13 else 7.35))<.01:e['t']=19.95 if src==13 else 7.25
  for t,pt in adds[src]:
   if p['id'] in [1,496]:pt=[960+(pt[0]-540)*.5625,pt[1]*.5625]
   p['events'].append({'t':t,'point':pt,'kind':'outlined-square','label':'brown outline square before collection'})
 else:
  t=22.45 if p['id'] in [671,811] else 8.75
  p['events'].append({'t':t,'point':[413,930],'layer':'ARROW GLYPH FX | lower right','kind':'outlined-square','label':'outlined collection square'})
  p['squares'].append([413,930])
 p['events'].sort(key=lambda e:e['t']);p['handSizeMultiplier']=.30;p['timingNote']='Solid and outlined choice squares; press before train arrival; hand size 30% of previous.'
(root/'outline-small-hand-plan.json').write_text(json.dumps(plans,indent=2));print([(p['name'],len(p['events'])) for p in plans])
