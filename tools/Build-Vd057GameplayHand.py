import json,math
from pathlib import Path
root=Path(__file__).resolve().parents[1];data=json.loads((root/'.ae-codex/vd057-train-contact-tracks.json').read_text());items=json.loads((root/'.ae-codex/transfer30to58-detail.json').read_text(encoding='utf-8-sig'));master=next(a for a in items if a['id']==5372);base=next(a for a in master['layers'] if a['id']==5528)['start']
def mapped(raw,scene):
 if scene==2:return base+(raw-49.4)*.8
 return (raw-15.0333333333)*.8 if raw<18.833333 else (raw*.8-11.2666666667)*.8
last={};cues=[]
for v in data['visits']:
 if v['scene']==1 and v['raw']<15.4:continue
 key=(v['scene'],v['tile']);prev=last.get(key)
 if prev is not None:
  between=[a for a in data['tracks'][str(v['scene'])] if prev['raw']<a['raw']<v['raw']]
  if not any(math.dist(a['screen'],[v['point'][0]/3,v['point'][1]/3])>55 for a in between):continue
 t=round(max(0,mapped(v['raw'],v['scene'])-.0333333333)*30)/30
 if v['scene']==1 and t>8:continue
 if cues and t-cues[-1]['time']<.17:
  if v['distance']>=cues[-1]['verifiedTrainDistance']:continue
  cues.pop()
 cues.append(dict(time=t,point=v['point'],scene=v['scene'],raw=v['raw'],tile=v['tile'],verifiedTrainDistance=v['distance']));last[key]=v
# At a stop, contact precedes departure, rather than firing on arrival while
# the train is unloading. Other junction contacts lead the visible turn.
departure_raw={(1,0):21.3,(1,5):25.5,(2,0):56.5667}
causal=[]
for cue in cues:
 s,k,raw=cue['scene'],cue['tile'],cue['raw'];onset=None
 if s==1 and k in (0,5):onset=mapped(departure_raw[(s,k)],s)
 elif s==2 and k==0 and raw<60:onset=mapped(56.5667,s)
 elif s==2 and k==1 and 63<raw<65:onset=mapped(70.9667,s)
 elif s==2 and k==2 and 74<raw<76:onset=mapped(78.0667,s)
 elif s==2 and k==2 and 96<raw<98:onset=mapped(99.8667,s)
 elif s==2 and k==1 and raw>103:continue # train remains stopped at the finish
 cue['time']=round((onset-.30 if onset is not None else cue['time']-.20)*30)/30
 cue['motionOnset']=onset if onset is not None else cue['time']+.25
 causal.append(cue)
causal.append(dict(time=1/30,point=[968.7,926.7],scene=1,raw=15.0333333,tile=4,motionOnset=.30,verifiedTrainDistance=0))
cues=sorted(causal,key=lambda a:a['time'])
path=[]
for scene in [1,2]:
 for tr in data['tracks'][str(scene)]:
  t=mapped(tr['raw'],scene)
  if t<0 or (scene==1 and t>7.9) or (scene==2 and t<11.2):continue
  x,y=tr['screen'];x*=3;y*=3
  # A hovering finger follows the head without pretending to press a stale tile.
  x+=-52 if x>900 else 52;y+=58
  x=max(75,min(1000,x));y=max(90,min(1780,y))
  path.append([round(t,5),round(x,2),round(y,2)])
first=path[0];path.append([0,first[1],first[2]]);path.extend([[8.3,960,1670],[10.5,960,1670],[11.05,200,650]])
path.sort();path.append([master['duration'],path[-1][1],path[-1][2]])
plan=dict(comp=5372,baseStart=base,duration=master['duration'],cues=cues,path=path,tipAnchor=[130,130],portalZoom=[9.6,11.0],notes='Current gameplay: press and release precede train departure/turn. Continuous moving hover; hide only during portal camera zoom 9.6-11.0. No terminal click while train stays stopped.')
(root/'.ae-codex/vd057-gameplay-hand-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(dict(baseStart=base,contacts=len(cues),pathSamples=len(path),cues=cues),indent=2))
