import json,subprocess,math,array
from pathlib import Path
root=Path(__file__).resolve().parents[1]
items={x['id']:x for x in json.loads((root/'.ae-codex/transfer30to58-detail.json').read_text(encoding='utf-8-sig'))}
ff=r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
def ta(raw):
 return (raw-15.0333333333)*.8 if raw<18.833333 else (raw*.8-11.2666666667)*.8
def tb(raw):return 9.0333333333+(raw-49.4)*.8
taps=[]
for raw,x,y in [(15.3,150,155),(16.3,90,78),(21.05,90,78),(22.4,120,155),(23.1,150,155),(25.7,90,230),(28.5,30,230)]:taps.append(dict(time=ta(raw),raw=raw,scene=1,point=[x*8,y*8]))
for raw,x,y in [(56.35,36,92),(57.05,66,120),(58.25,66,172),(59.75,66,231),(60.8,113,231),(61.95,113,173),(62.45,119,128),(63,152,98),(68.55,36,92),(70.65,66,120),(72.8,66,172),(73.55,113,173),(74.15,119,128),(77.8,152,98),(80.8,36,92),(82.8,66,120),(84.7,66,172),(85.8,119,128),(87,113,173),(88.5,66,231),(90,113,231),(91.2,113,173),(92.7,66,172),(93.5,66,231),(94.6,113,231),(95.6,113,173),(96.5,119,128),(100,152,98),(102.2,119,128)]:taps.append(dict(time=tb(raw),raw=raw,scene=2,point=[x*8,y*8]))
sounds=[]
def cue(kind,t,dur,source,offset,target):sounds.append(dict(kind=kind,time=round(t*30)/30,duration=dur,source=source,offset=offset,target=target))
for c in taps:cue('TAP',c['time'],.12,1563,0,-17)
for t in [.03,4.5,11.15,14.6,24.8,32.4,39.9,47.4]:cue('TRAIN START',t,.24,5227,.04,-19)
for scene,clusters in [(1,[(15.1,15.55),(16.3,16.7),(21.35,22.05),(23.65,24.3),(25.45,25.8)]),(2,[(56.65,57.2),(59.25,59.8),(61.15,61.65),(62.35,63),(71.55,72),(74.1,74.55),(77.7,78.05),(82.6,83.15),(85.35,85.75),(89.65,90.15),(93.2,93.7),(95.05,95.65),(97.8,98.25),(102.45,103)])]:
 for a,b in clusters:
  r=a
  while r<=b+.001:
   cue('BLOCK COLLECT',ta(r) if scene==1 else tb(r),.12,1563,0,-12)
   r+=.2
for scene,raws in [(1,[16.95,17.2,17.5,18.65,19,19.3,19.65]),(2,[63.55,63.8,64.05,65.55,65.85,66.15,66.5,67.6,67.9,68.2,69.5,69.8,70.1,74.8,75.1,75.45,76.6,76.9,77.2,80.15,80.45,81,96.85,97.15,97.5,98.65,98.95,99.2,101.25,101.55,101.85,104,104.3])]:
 for r in raws:cue('TRAY / DISAPPEAR',ta(r) if scene==1 else tb(r),.3,5109,.02,-9)
for t,source in [(9.6,5107),(10.85,5104),(53.3,5107)]:cue('PORTAL',t,.65,source,.02,-10)
for t in [9.82,10.57,53.5]:cue('PORTAL WHOOSH',t,.32,5227,.02,-17)
# Measure exactly the source trims used by AE; normalize by peak, retain headroom.
for c in sounds:
 raw=subprocess.run([ff,'-v','error','-ss',str(c['offset']),'-i',items[c['source']]['file'],'-t',str(c['duration']),'-vn','-ac','2','-ar','24000','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
 vals=array.array('f');vals.frombytes(raw);peak=max(map(abs,vals),default=1e-5)
 c['gain']=round(c['target']-20*math.log10(max(peak,1e-5)),3);c['file']=items[c['source']]['file']
plan=dict(target=5372,sourceComp=785,duration=59.5666666667,taps=taps,sounds=sounds,music=dict(source=951,file=items[951]['file'],gain=-26),notes='Hand + sound only. No original visual properties or story changes. Same normalized sources across scenes; tray 3dB above collection; short train onset accents.')
(root/'.ae-codex/vd057-transfer-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(json.dumps(dict(taps=len(taps),sounds=len(sounds),gainRange=[min(x['gain'] for x in sounds),max(x['gain'] for x in sounds)])))
