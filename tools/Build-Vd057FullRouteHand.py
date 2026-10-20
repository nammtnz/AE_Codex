import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / '.ae-codex/vd057-train-contact-tracks.json').read_text())
prior = json.loads((ROOT / '.ae-codex/vd057-destination-hand-plan.json').read_text())
items = json.loads((ROOT / '.ae-codex/transfer30to58-detail.json').read_text(encoding='utf-8-sig'))
comp = next(c for c in items if c['id'] == 5372)
base = next(l for l in comp['layers'] if l['id'] == 5528)['start']


def mapped(raw, scene):
    if scene == 2:
        return base + (raw - 49.4) * .8
    if raw < 18.8333333333:
        return (raw - 15.0333333333) * .8
    return (raw * .8 - 11.2666666667) * .8


def nearest(a, b, p):
    dx, dy = b[0] - a[0], b[1] - a[1]
    den = dx * dx + dy * dy
    q = max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den)) if den else 0
    xy = [a[0] + q * dx, a[1] + q * dy]
    return math.dist(xy, p), q


# The red engine flashes white during collection. Those gaps were the reason
# the old red-only detection omitted junctions. The missing visits below were
# checked directly in the source-frame sheets, including each reverse pass.
visits = [
    (1, 21.55, 'UPPER PORTAL', (179.2,241)),
    (1, 21.65, 'MIDDLE PORTAL', (179.2,275)),
    (1, 21.75, 'LOWER CENTRAL PORTAL', (179.2,309)),
    (1, 25.7657, 'BOTTOM PORTAL', (179.2,466)),
    (2, 57.85, 'LEFT UPPER GATE', (122.5,346.5)),
    (2, 58.85, 'RIGHT UPPER GATE', (233,346.5)),
    (2, 59.1333, 'RIGHT LOWER GATE', (233,392)),
    (2, 61.7, 'LEFT LOWER GATE', (122.5,392)),
    (2, 62.0333, 'LEFT UPPER GATE', (122.5,346.5)),
    (2, 62.8, 'LEFT MIDDLE RETURN', (122.5,259.4)),
    (2, 71.4, 'LEFT OUTER RETURN', (30.4,172.6)),
    (2, 72.8333, 'LEFT UPPER GATE', (122.5,346.5)),
    (2, 73.2667, 'RIGHT UPPER GATE', (233,346.5)),
    (2, 73.8, 'RIGHT MIDDLE RETURN', (233,259.3)),
    (2, 78.4, 'RIGHT OUTER EXIT', (325.5,177.5)),
    (2, 83.4333, 'LEFT UPPER GATE', (122.5,346.5)),
    (2, 84.0667, 'RIGHT UPPER GATE', (233,346.5)),
    (2, 85.1667, 'RIGHT MIDDLE RETURN', (233,259.3)),
    (2, 86.1667, 'RIGHT OUTER TURN', (325.5,177.5)),
    (2, 87.9667, 'RIGHT UPPER GATE', (233,346.5)),
    (2, 88.4667, 'LEFT UPPER GATE', (122.5,346.5)),
    (2, 88.7333, 'LEFT LOWER GATE', (122.5,392)),
    (2, 91.4, 'RIGHT LOWER GATE', (233,392)),
    (2, 91.8, 'LEFT LOWER GATE', (122.5,392)),
    (2, 94.5333, 'RIGHT LOWER GATE', (233,392)),
    (2, 94.7667, 'RIGHT UPPER GATE', (233,346.5)),
    (2, 95.6, 'RIGHT MIDDLE RETURN', (233,259.3)),
    (2, 100.2, 'RIGHT OUTER EXIT', (325.5,177.5)),
]
extra = [dict(scene=s, tile=label, label=label, raw=raw, arrival=mapped(raw,s),
              point=[round(v*3,2) for v in point], distance=None, intermediate=True)
         for s,raw,label,point in visits]
events = []
for e in prior['cues']:
    events.append({k: e[k] for k in ('scene', 'tile', 'raw', 'point', 'distance')})
    events[-1]['arrival'] = mapped(e['raw'], e['scene'])
    events[-1]['intermediate'] = False
events.extend(extra)
events.sort(key=lambda e: (e['scene'], e['raw']))


def ceil_frame(t):
    return math.ceil(t*30-.00001)/30


path=[]
for i,e in enumerate(events):
    e['arrival']=ceil_frame(e['arrival'])
    if i==0:
        e.update(moveStart=0,handArrival=0,time=.1)
        path.append([0,*e['point']])
    else:
        prev=events[i-1]
        start=prev['arrival']
        if prev['scene']!=e['scene']:
            start=10.6666666666667
            hand_arrival=11.1333333333333
            click=11.1666666666667
        else:
            gap=e['arrival']-start
            if gap<2/30-.00001:
                raise RuntimeError(f'Cannot cover distinct junctions within two frames: {prev} -> {e}')
            if gap<.2:
                duration=1/30
                hand_arrival=start+duration
                click=hand_arrival
            else:
                duration=max(1/30,min(.4,math.floor((gap-.1333333333)*30+.00001)/30))
                hand_arrival=start+duration
                click=hand_arrival+1/30
        e.update(moveStart=start,handArrival=hand_arrival,time=click)
        prev['holdUntil']=start
        path.extend([[start,*prev['point']],[hand_arrival,*e['point']]])
    assert e['time']<e['arrival']-.015,e
events[-1]['holdUntil']=comp['duration']
path.append([comp['duration'],*events[-1]['point']])
for i,e in enumerate(events):
    gap=events[i+1]['time']-e['time'] if i+1<len(events) else 1
    e['pulseDuration']=min(.1,gap*.48)
    e['soundDuration']=min(.12,gap*.85)
    assert e['holdUntil']>=e['arrival']-.00001
plan=dict(comp=5372,name=comp['name'],duration=comp['duration'],baseStart=base,
          tipAnchor=[130,130],portalHidden=[9.6,11],cues=events,path=path,
          addedIntermediates=len(extra),sequence='Click every intermediate junction in route order; stay at each clicked node until the train arrives; then go to the next passed node. Includes both portal lanes, reverse visits and outer turns.')
(ROOT / '.ae-codex/vd057-full-route-hand-plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps(dict(contacts=len(events),added=len(extra),route=[dict(index=i,scene=e['scene'],tile=e['tile'],
      click=round(e['time'],4),arrival=round(e['arrival'],4)) for i,e in enumerate(events)]),indent=2))
