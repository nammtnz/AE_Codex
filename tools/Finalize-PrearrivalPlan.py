from pathlib import Path
import json,sys
root=Path(sys.argv[1]);data=json.loads((root/'direction-square-plan.json').read_text());new=[]
# Timing reviewed against captured gameplay. Omit clicks whose scene opens
# with the train already covering the control square.
static={13:[(1,1.70),(3,12.25),(4,13.00),(5,16.60),(6,17.50),(7,18.10),(8,20.10),(9,25.10),(10,25.50)],477:[(0,.15),(2,3.70),(3,5.70),(4,7.35),(5,9.55),(6,10.00)]}
projected={671:[1.10,3.35,6.15,8.75,10.55,12.35,13.20,14.40,19.95,22.20],811:[1.10,3.35,6.15,8.75,10.55,12.35,13.20,14.40,19.95,22.20],1059:[.20,1.30,1.65,3.40,3.85,4.35,4.75,5.10,7.20,8.50],1132:[.20,1.30,1.65,3.40,3.85,4.35,4.75,5.10,7.20,8.50]}
for p in data:
 q=dict(p);q['previousEvents']=p['events'];events=[]
 if p['mode']=='static':
  src=13 if p['id'] in [13,1] else 477
  for index,t in static[src]:events.append(dict(p['events'][index],t=t,previousTime=p['events'][index]['t']))
 else:
  for e,t in zip(p['events'],projected[p['id']]):events.append(dict(e,t=t,previousTime=e['t']))
 q['events']=events;q['timingNote']='Press before locomotive reaches square; white ripple finishes before crossing; opening-on-square events omitted.';new.append(q)
(root/'prearrival-reviewed-plan.json').write_text(json.dumps(new,indent=2));print([(p['name'],[e['t'] for e in p['events']]) for p in new])
