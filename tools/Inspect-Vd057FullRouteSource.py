import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ff = 'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
out = ROOT / '.ae-codex/inspection/vd057-full-route-source'
out.mkdir(exist_ok=True)
segments = [(57.2, 59.4), (60.4, 63.6), (70.9, 71.9), (85.7, 87.3)]
for number, (start, end) in enumerate(segments, 7):
    pixels = subprocess.run([ff, '-v', 'error', '-ss', str(start), '-i',
        'E:/Task/Snacky Dash/RWD_VD007/FT/Movie_025.mp4', '-t', str(end-start),
        '-vf', 'fps=5,scale=432:768,crop=360:640:38:64', '-an', '-f', 'rawvideo',
        '-pix_fmt', 'rgb24', 'pipe:1'], capture_output=True, check=True).stdout
    frames = np.frombuffer(pixels, dtype='uint8').reshape(-1, 640, 360, 3)
    rows = (len(frames) + 7) // 8
    sheet = Image.new('RGB', (2160, rows * 500))
    d = ImageDraw.Draw(sheet)
    for i, frame in enumerate(frames):
        im = Image.fromarray(frame).resize((270, 480))
        sheet.paste(im, (i % 8 * 270, i // 8 * 500))
        d.text((i % 8 * 270 + 3, i // 8 * 500 + 482), f'{start+i/5:.2f}', fill='white')
    sheet.save(out / f'segment{number}.png')
    print(number, start, end, len(frames))
