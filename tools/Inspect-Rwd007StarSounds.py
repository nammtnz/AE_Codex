import json, math, subprocess
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
base = Path('E:/Audio/SFX/Cartoon')
ffmpeg = r'C:\Users\nguye\AppData\Local\XGetter\externals\ffmpeg.exe'
choices = [('star', '10 Empire Warriors/sfx_ui_star.mp3', .30),
           ('pop', 'Button/cartoon-pop.mp3', .22),
           ('victory', '10 Empire Warriors/sfx_ui_victory.mp3', 1.25),
           ('complete1', 'Level complete/Level Complete 1.wav', 1.60),
           ('complete2', 'Level complete/Level Complete 2.wav', 1.60),
           ('completed1', 'Level complete/Level Completed 1.wav', 1.60),
           ('completed2', 'Level complete/Level Completed 2.wav', 1.60),
           ('mountain', 'Level complete/Mountain Audio - Level Complete/Mountain Audio - Level Complete.wav', 1.60)]
rows = []
for kind, rel, maximum in choices:
    path = base / rel
    if not path.exists():
        raise FileNotFoundError(path)
    result = subprocess.run([ffmpeg, '-v', 'error', '-i', str(path), '-vn', '-ac', '2', '-ar', '48000', '-f', 'f32le', 'pipe:1'], capture_output=True, check=True)
    x = np.frombuffer(result.stdout, dtype='<f4').reshape(-1, 2)
    active = np.flatnonzero(np.max(np.abs(x), axis=1) > 10 ** (-38 / 20))
    offset = max(0, active[0] / 48000 - .004)
    duration = min(maximum, len(x) / 48000 - offset)
    cut = x[round(offset * 48000):round((offset + duration) * 48000)]
    peak = 20 * math.log10(max(float(np.max(np.abs(cut))), 1e-12))
    rms = 20 * math.log10(max(float(np.sqrt(np.mean(cut ** 2))), 1e-12))
    rows.append(dict(kind=kind, file=str(path), totalDuration=round(len(x)/48000, 4), offset=float(offset), duration=float(duration), activeEnd=round((active[-1] + 1) / 48000, 4), peak_dbfs=round(peak, 2), rms_dbfs=round(rms, 2)))
(root / '.ae-codex/rwd007-star-sound-assets.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
print(json.dumps(rows, indent=2))
