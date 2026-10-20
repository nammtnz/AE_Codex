import json, math, subprocess
from pathlib import Path
import numpy as np

root = Path(__file__).resolve().parents[1]
data = json.loads((root / '.ae-codex/rwd008-mode-audio-mix-metadata.json').read_text(encoding='utf-8-sig'))
rate = 48000
ffmpeg = r'C:\Users\nguye\AppData\Local\XGetter\externals\ffmpeg.exe'
sources = {}
reports = []
for comp in data['comps']:
    mix = np.zeros((round(comp['duration']*rate),2),dtype=np.float64)
    for cue in comp['cues']:
        if cue['file'] not in sources:
            pcm = subprocess.run([ffmpeg,'-v','error','-i',cue['file'],'-vn','-ac','2','-ar',str(rate),'-f','f32le','pipe:1'],capture_output=True,check=True).stdout
            sources[cue['file']] = np.frombuffer(pcm,dtype='<f4').reshape(-1,2)
        src=sources[cue['file']]
        start=round(cue['start']*rate); offset=round(cue['offset']*rate)
        n=min(round((cue['end']-cue['start'])*rate),len(mix)-start,len(src)-offset)
        if n<=0: raise ValueError('Empty cue '+cue['name'])
        env=np.array([[r[0],*r[1]] for r in cue['levels']])
        ts=np.arange(n)/rate
        gain=np.column_stack([10**(np.interp(ts,env[:,0],env[:,ch+1])/20) for ch in range(2)])
        mix[start:start+n] += src[offset:offset+n]*gain
    spans=[]
    for cue in comp['cues']:
        if not cue['name'].startswith('VOICE | DIFFICULTY | '): continue
        part=mix[round(cue['start']*rate):round(cue['end']*rate)]
        spans.append(dict(voice=cue['name'],peak_dbfs=round(20*math.log10(max(float(np.max(np.abs(part))),1e-12)),2),clipped_samples=int(np.sum(np.abs(part)>=1))))
    reports.append(dict(comp=comp['name'],scope=comp['scope'],announcement_spans=spans))
(root/'.ae-codex/rwd008-mode-audio-mix-check.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports,indent=2))
if any(s['clipped_samples'] for c in reports for s in c['announcement_spans']): raise RuntimeError('Voice/music/warning mix clips')
