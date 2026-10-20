import json
import math
import subprocess
from pathlib import Path

import numpy as np

root = Path(__file__).resolve().parents[1]
metadata = json.loads((root / '.ae-codex/rwd007-audio-mix-metadata.json').read_text(encoding='utf-8-sig'))
ffmpeg = r'C:\Users\nguye\AppData\Local\XGetter\externals\ffmpeg.exe'
sample_rate = 48000
sources = {}
for comp in metadata['comps']:
    for cue in comp['cues']:
        filename = cue['file']
        if filename in sources:
            continue
        data = subprocess.run([ffmpeg, '-v', 'error', '-i', filename, '-vn', '-ac', '2', '-ar', str(sample_rate), '-f', 'f32le', 'pipe:1'], check=True, capture_output=True).stdout
        sources[filename] = np.frombuffer(data, dtype='<f4').reshape(-1, 2)

reports = []
for comp in metadata['comps']:
    mix = np.zeros((round(comp['duration'] * sample_rate), 2), dtype=np.float64)
    accents = np.zeros_like(mix)
    for cue in comp['cues']:
        start = round(cue['start'] * sample_rate)
        duration = min(round((cue['end'] - cue['start']) * sample_rate), len(mix) - start)
        offset = round(cue['offset'] * sample_rate)
        source = sources[cue['file']]
        duration = min(duration, len(source) - offset)
        if duration <= 0:
            raise ValueError(f"Empty audio source cut: {cue['name']}")
        times = np.arange(duration) / sample_rate
        envelope = np.asarray([[row[0], *row[1]] for row in cue['levels']])
        gains = np.column_stack([10 ** (np.interp(times, envelope[:, 0], envelope[:, channel + 1]) / 20) for channel in range(2)])
        signal = source[offset:offset + duration] * gains
        mix[start:start + duration] += signal
        if cue['name'].startswith('RWD007 SFX | '):
            accents[start:start + duration] += signal
    peak = float(np.max(np.abs(mix)))
    dbfs = 20 * math.log10(max(peak, 1e-12))
    rms = 20 * math.log10(max(float(np.sqrt(np.mean(mix ** 2))), 1e-12))
    clips = int(np.sum(np.abs(mix) >= 1))
    reports.append({'comp': comp['name'], 'peakDbFS': round(dbfs, 2), 'rmsDbFS': round(rms, 2), 'clippedSamples': clips, 'newAccentsPeakDbFS': round(20 * math.log10(max(float(np.max(np.abs(accents))), 1e-12)), 2), 'verification': 'Offline mix from current AE source cuts and sampled stereo level envelopes; no project/video rendering.'})
(root / '.ae-codex/rwd007-audio-mix-check.json').write_text(json.dumps(reports, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(reports, indent=2, ensure_ascii=False))
