import json
import math
import subprocess
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ff = 'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
tracks = {}
for scene, file, start, duration, xoff in [(1, 'Movie_015.mp4', 15, 14.7, 36.333333),
        (2, 'Movie_025.mp4', 54.2666666667, 50.7, 37.666667)]:
    raw = subprocess.run([ff, '-v', 'error', '-ss', str(start), '-i',
        'E:/Task/Snacky Dash/RWD_VD007/FT/' + file, '-t', str(duration),
        '-vf', 'fps=30,scale=180:320', '-an', '-f', 'rawvideo', '-pix_fmt', 'rgb24',
        'pipe:1'], capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, dtype='uint8').reshape(-1, 320, 180, 3)
    masks = []
    for frame in frames:
        im = frame.astype('int16'); r, g, b = [im[:, :, k] for k in range(3)]
        mask = (r > 140) & (g < 140) & (b < 110) & (r-g > 65) & (r-b > 65)
        mask[:80] = False; mask[275:] = False; mask[:, :14] = False; mask[:, 166:] = False
        masks.append(mask)
    fixed = np.stack(masks).mean(axis=0) > .45
    route = []; previous = None
    for n, (frame, mask) in enumerate(zip(frames, masks)):
        pixels = set(np.flatnonzero(mask & ~fixed)); candidates = []
        while pixels:
            seed = pixels.pop(); stack = [seed]; group = [seed]
            while stack:
                at = stack.pop()
                for j in (at-1, at+1, at-180, at+180):
                    if j in pixels:
                        pixels.remove(j); stack.append(j); group.append(j)
            if not 2 <= len(group) <= 80:
                continue
            xs = [a % 180 for a in group]; ys = [a // 180 for a in group]
            colors = frame[ys, xs].astype(int)
            red = np.mean(colors[:,0] - colors[:,1])
            x, y = sum(xs)/len(xs), sum(ys)/len(ys)
            score = len(group) * .8 + red * .12
            if previous is not None:
                score -= min(math.dist((x, y), previous), 45) * .22
            candidates.append((score, x, y, len(group), red))
        if candidates:
            score, x, y, area, red = max(candidates)
            previous = (x, y)
            route.append(dict(raw=round(start+n/30,6), screen=[round(x*2.4-xoff,3),round(y*2.4-64,3)],
                              pixels=area, red=round(red,1)))
    tracks[str(scene)] = route
    print(scene, 'frames', len(frames), 'head detections', len(route))
(ROOT / '.ae-codex/vd057-full-route-tracks.json').write_text(json.dumps(dict(tracks=tracks), indent=2))
