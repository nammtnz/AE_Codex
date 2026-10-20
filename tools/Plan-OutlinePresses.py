from pathlib import Path
import json,math,sys
root=Path(sys.argv[1]);tracks={p['id']:p['track'] for p in json.loads((root/'continuous-plan.json').read_text())};projections={p['id']:p['samples'] for p in json.loads((root/'outline-projection.json').read_text())}
def intervals(cid,point,start,end):
 hits=[]
 for q in tracks[cid]:
  t=q['t']
  if not start<=t<end:continue
  xy=point if point else min(projections[cid],key=lambda v:abs(v[0]-t))[1:]
  dx,dy={1:(1,0),2:(0,1),3:(-1,0),4:(0,-1),0:(0,0)}[q['dir']];d=math.hypot(q['x']+dx*q['w']*.5-xy[0],q['y']+dy*q['w']*.5-xy[1])/max(q['w'],15)
  if d<1.2:hits.append((t,round(d,2)))
 groups=[]
 for t,d in hits:
  if not groups or t-groups[-1][-1][0]>.26:groups.append([])
  groups[-1].append((t,d))
 return [(g[0][0],g[-1][0],min(g,key=lambda v:v[1])) for g in groups]
for cid in [13,477]:
 for pt,start,end in [([540,607],0,9.65 if cid==13 else 2.9),([540,959],9.7 if cid==13 else 2.9,19.7 if cid==13 else 7.1),([540,1301],9.7 if cid==13 else 2.9,19.7 if cid==13 else 7.1),([328,464],19.8 if cid==13 else 7.1,27 if cid==13 else 12),([752,464],19.8 if cid==13 else 7.1,27 if cid==13 else 12)]:print(cid,pt,intervals(cid,pt,start,end))
for cid in projections:print(cid,'outline',intervals(cid,None,0,27 if cid in [671,811] else 12))
