import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
items=json.loads((root/'.ae-codex/transfer30to58-detail.json').read_text(encoding='utf-8-sig'));c=next(i for i in items if i['id']==5372);base=next(l for l in c['layers'] if l['id']==5528)['start']
def tb(raw):return base+(raw-49.4)*.8
def ta(raw):return (raw-15.0333333333)*.8 if raw<18.833333 else (raw*.8-11.2666666667)*.8
def frame(t):return round(t*30)/30
# Movement begins in the existing footage. Every press finishes before it;
# transit begins after the train is stopped, except the opening posed contact.
stops=[dict(time=1/30,point=[968.7,926.7],motionOnset=ta(15.5),moveStart=0,arrive=0,label='OPENING START'),
 dict(time=frame(ta(21.3)-.30),point=[537.6,443.1],motionOnset=ta(21.3),moveStart=1.8,arrive=2.25,label='FIRST TRAY DEPARTURE'),
 dict(time=frame(ta(25.5)-.30),point=[968.7,1467],motionOnset=ta(25.5),moveStart=6.65,arrive=6.9,label='LOWER RIGHT DEPARTURE'),
 dict(time=frame(tb(56.5667)-.30),point=[91.2,517.8],motionOnset=tb(56.5667),moveStart=tb(55.5),arrive=tb(56.0),label='SECOND SCENE START'),
 dict(time=frame(tb(70.9667)-.30),point=[367.5,510],motionOnset=tb(70.9667),moveStart=tb(63.8),arrive=tb(64.5),label='LEFT TRAY DEPARTURE'),
 dict(time=frame(tb(78.0667)-.30),point=[699,510],motionOnset=tb(78.0667),moveStart=tb(75.0),arrive=tb(75.65),label='RIGHT TRAY DEPARTURE'),
 dict(time=frame(tb(99.8667)-.30),point=[699,510],motionOnset=tb(99.8667),moveStart=tb(96.8),arrive=tb(97.5),label='LAST RIGHT TRAY DEPARTURE')]
rest=[970,1770];path=[]
for i,s in enumerate(stops):
 pt=s['point'];hover=[pt[0]+(12 if pt[0]<900 else -12),pt[1]-18]
 if i==0:path.append([0,*hover])
 else:path.extend([[s['moveStart'],*rest],[s['arrive'],*hover]])
 path.extend([[s['motionOnset']+.20,*hover],[s['motionOnset']+.62,*rest]])
path.append([c['duration'],*rest]);path.sort()
for s in stops:
 assert s['time']+.18 < s['motionOnset']
 assert s['arrive']<=s['time']-.06 or s['time']<.1
plan=dict(comp=5372,duration=c['duration'],baseStart=base,cues=stops,path=path,tipAnchor=[130,130],portalZoom=[9.6,11],sequence='Train stops; hand moves to actual orange switch, settles, presses and releases; train starts; hand leaves. No tracking or clicks while train is already moving.')
(root/'.ae-codex/vd057-stop-click-plan.json').write_text(json.dumps(plan,indent=2));print(json.dumps(dict(contacts=len(stops),motionLead=[round(s['motionOnset']-s['time'],3) for s in stops],stops=stops),indent=2))
