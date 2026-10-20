import json
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageOps

root = Path(__file__).resolve().parents[1]
out = root / '.ae-codex/inspection/rwd007-click-audit-20261013'
out.mkdir(parents=True, exist_ok=True)
ffmpeg = r'C:\Users\nguye\AppData\Local\XGetter\externals\ffmpeg.exe'
video = r'E:\Task\Snacky Dash\New folder\FT\Movie_005.mp4'
data = subprocess.run([ffmpeg, '-v', 'error', '-ss', '37.4', '-i', video, '-t', '20.64', '-vf', 'fps=10,scale=360:640', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1'], capture_output=True, check=True).stdout
frames = np.frombuffer(data, dtype=np.uint8).reshape(-1, 640, 360, 3)
track = []
for n, frame in enumerate(frames):
    rgb = frame.astype(np.int16)
    mask = (rgb[:, :, 0] > 145) & (rgb[:, :, 1] < 120) & (rgb[:, :, 2] < 115)
    mask[:140] = False
    mask[520:] = False
    ys, xs = np.where(mask)
    if len(xs) > 8:
        track.append({'raw': round(37.4 + n / 10, 3), 'x': round(float(np.median(xs)) * 3, 1), 'y': round(float(np.median(ys)) * 3, 1)})

(out / 'locomotive-track.json').write_text(json.dumps(track, indent=2), encoding='utf-8')
times = [37.4, 37.7, 39.3, 40.4, 41.8, 43.0, 44.5, 46.0, 47.5, 49.0, 50.8, 51.5, 53.0, 54.0, 55.0, 56.0, 57.0, 58.0]
sheet = Image.new('RGB', (1800, 1320), (24, 24, 30))
draw = ImageDraw.Draw(sheet)
for n, t in enumerate(times):
    ix = min(len(frames) - 1, round((t - 37.4) * 10))
    pic = Image.fromarray(frames[ix]).crop((30, 140, 330, 520)).resize((280, 400))
    sheet.paste(pic, ((n % 6) * 300 + 5, (n // 6) * 440 + 25))
    row = min(track, key=lambda row: abs(row['raw'] - t))
    draw.text(((n % 6) * 300 + 5, (n // 6) * 440 + 5), f"raw {t:.1f} head~{row['x']:.0f},{row['y']:.0f}", fill='white')
sheet.save(out / 'source-route-review.jpg')
points = {'lower left': (365, 1173), 'lower right': (765, 1173), 'left top': (165, 657), 'right middle': (765, 657), 'right top': (915, 657), 'top middle': (615, 470), 'center': (615, 937), 'delivery': (415, 930), 'gate': (810, 1173), 'bridge top': (615, 657)}
for label, point in points.items():
    hits = [row for row in track if np.hypot(row['x'] - point[0], row['y'] - point[1]) < 55]
    groups = []
    for row in hits:
        if not groups or row['raw'] - groups[-1][-1]['raw'] > .3:
            groups.append([row])
        else:
            groups[-1].append(row)
    print(label, point, [(g[0]['raw'], g[-1]['raw']) for g in groups])
