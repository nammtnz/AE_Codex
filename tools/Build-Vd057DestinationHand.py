import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / '.ae-codex/vd057-train-contact-tracks.json').read_text())
items = json.loads((ROOT / '.ae-codex/transfer30to58-detail.json').read_text(encoding='utf-8-sig'))
comp = next(c for c in items if c['id'] == 5372)
base = next(l for l in comp['layers'] if l['id'] == 5528)['start']


def mapped(raw, scene):
    if scene == 2:
        return base + (raw - 49.4) * .8
    if raw < 18.8333333333:
        return (raw - 15.0333333333) * .8
    return (raw * .8 - 11.2666666667) * .8


tiles = {
    1: [(179.2, 147.7), (35.5, 241.1), (322.9, 241),
        (250.9, 308.8), (322.9, 308.9), (322.9, 489),
        (179, 556.5), (179.2, 421.5), (35.5, 489)],
    2: [(30.4, 172.6), (122.5, 170), (233, 170),
        (122.5, 259.4), (233, 259.3), (122.5, 519.4),
        (233, 519.3), (325.5, 177.5)],
}
events = []
for scene in (1, 2):
    tracks = data['tracks'][str(scene)]
    for tile, pt in enumerate(tiles[scene]):
        hits = [a for a in tracks if math.dist(a['screen'], pt) < 30]
        groups = []
        for a in hits:
            # Missing detections during white flashes must not turn a stop
            # into repeated target visits.
            if not groups:
                groups.append([a])
                continue
            prior = groups[-1][-1]
            between = [b for b in tracks if prior['raw'] < b['raw'] < a['raw']]
            left_target = any(math.dist(b['screen'], pt) > 55 for b in between)
            if a['raw'] - prior['raw'] > .35 and left_target:
                groups.append([a])
            else:
                groups[-1].append(a)
        for group in groups:
            best = min(group, key=lambda a: math.dist(a['screen'], pt))
            if math.dist(best['screen'], pt) > 22:
                continue
            # Arrival is the first close contact, not a later best match
            # after the head has sat at an unloading tray for several seconds.
            close = next(a for a in group if math.dist(a['screen'], pt) < 22)
            raw = best['raw'] if group[-1]['raw'] - group[0]['raw'] < .8 else close['raw']
            if scene == 1 and tile == 7:
                raw = close['raw']  # brief pickup stop before returning upward
            if scene == 1 and tile == 4 and raw < 15.5:
                continue  # train starts here; the hand targets the NEXT tile
            events.append(dict(scene=scene, tile=tile, raw=raw,
                               arrival=mapped(raw, scene),
                               point=[round(v * 3, 2) for v in pt],
                               distance=round(math.dist(close['screen'], pt), 2)))

events.sort(key=lambda e: (e['scene'], e['raw']))


def frame(t):
    return round(t * 30) / 30


def ceil_frame(t):
    return math.ceil(t * 30 - .00001) / 30


path = []
for i, e in enumerate(events):
    e['arrival'] = ceil_frame(e['arrival'])
    if i == 0:
        e['moveStart'] = 0
        e['handArrival'] = 0
        e['time'] = .1
        path.append([0, *e['point']])
    else:
        prev = events[i - 1]
        start = ceil_frame(max(prev['arrival'] + 1 / 30, prev['time'] + .12))
        if prev['scene'] != e['scene']:
            start = 10.6666666666667
            hand_arrival = 11.1333333333333
        else:
            budget = e['arrival'] - start - 4 / 30
            duration = max(2 / 30, min(.4, frame(budget)))
            hand_arrival = frame(start + duration)
        e['moveStart'] = start
        e['handArrival'] = hand_arrival
        e['time'] = frame(hand_arrival + 1 / 30)
        prev['holdUntil'] = start
        path.extend([[start, *prev['point']], [hand_arrival, *e['point']]])
    assert e['time'] < e['arrival'] - .015, e
    assert e['handArrival'] <= e['time']
events[-1]['holdUntil'] = comp['duration']
path.append([comp['duration'], *events[-1]['point']])
for e in events:
    assert e['holdUntil'] >= e['arrival'], e

plan = dict(comp=5372, name=comp['name'], duration=comp['duration'], baseStart=base,
            tipAnchor=[130, 130], portalHidden=[9.6, 11], cues=events, path=path,
            sequence='Click next destination; hold fingertip exactly on that tile until train arrival; only then move to next destination. No neutral-rest or train-follow movement.')
(ROOT / '.ae-codex/vd057-destination-hand-plan.json').write_text(json.dumps(plan, indent=2))
print(json.dumps(dict(contacts=len(events), cues=[dict(scene=e['scene'], tile=e['tile'],
                 click=round(e['time'], 4), trainArrival=round(e['arrival'], 4),
                 holdUntil=round(e['holdUntil'], 4)) for e in events]), indent=2))
