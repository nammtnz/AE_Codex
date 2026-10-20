from pathlib import Path
from PIL import Image, ImageDraw
import json
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--start', type=float)
parser.add_argument('--end', type=float)
parser.add_argument('--step', type=float, default=1)
parser.add_argument('--label', default='full')
args = parser.parse_args()

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r'E:/Task/Snacky Dash/RWD_VD007/FT/Movie_009.mp4')
FFMPEG = r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
OUT = ROOT / '.ae-codex/inspection/rwd007-source009-feedback' / args.label
OUT.mkdir(parents=True, exist_ok=True)
W, H = 216, 384
frame_size = W * H * 3
if args.start is None:
    cmd = [FFMPEG, '-v', 'error', '-i', str(SOURCE), '-vf', 'fps=1/3,scale=216:384', '-an', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']
    data = subprocess.run(cmd, capture_output=True, check=True).stdout
    count = len(data) // frame_size
    times = [i*3 for i in range(count)]
else:
    times = []
    at = args.start
    while at <= args.end + .000001:
        times.append(round(at, 6))
        at += args.step
    data = b''
    for at in times:
        cmd = [FFMPEG, '-v', 'error', '-ss', str(at), '-i', str(SOURCE), '-frames:v', '1', '-vf', 'scale=216:384', '-an', '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']
        frame = subprocess.run(cmd, capture_output=True, check=True).stdout
        if len(frame) != frame_size:
            raise RuntimeError(f'Frame wrong size at {at}: {len(frame)}')
        data += frame
    count = len(times)
sheet = Image.new('RGB', (W * 6, (H + 24) * ((count + 5) // 6)), '#222222')
draw = ImageDraw.Draw(sheet)
for i in range(count):
    im = Image.frombytes('RGB', (W, H), data[i*frame_size:(i+1)*frame_size])
    im.save(OUT / f'source-{times[i]:06.2f}.png')
    x, y = (i % 6) * W, (i // 6) * (H + 24)
    sheet.paste(im, (x, y + 24))
    draw.text((x + 5, y + 5), f'Movie009 source {times[i]:.2f}s', fill='white')
sheet.save(OUT / 'contact-sheet.png')
result = {'source': str(SOURCE), 'times': times, 'frames': count, 'contactSheet': str(OUT / 'contact-sheet.png')}
(OUT / 'metadata.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result))
