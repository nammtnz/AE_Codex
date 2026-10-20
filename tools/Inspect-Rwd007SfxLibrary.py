import json, math, subprocess
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
base=Path('E:/Audio/SFX/Cartoon')
ffmpeg=r'C:\Users\nguye\AppData\Local\XGetter\externals\ffmpeg.exe'
choices=[('zap','Energy/SynthZap EC03_54_3.wav',.75),
 ('electric','Magic Spell/magic-spell-pack-JY7QKXR/Electric - Cast Spell 1.wav',.8),
 ('impact','Magic Spell/magic-spell-pack-JY7QKXR/Electric - Spell Impact 1.wav',.45),
 ('whoosh','Energy/electric-whoosh-2YPMSQ4/Electric Whoosh 1.wav',.65),
 ('startup','Energy/Electrical-Startup_TTX021004.wav',1),
 ('energy','Energy/energy hit.wav',.5),
 ('select','Button/interface-pack/Selection.wav',.18),
 ('click','Button/Game Menu Click 4.mp3',.18),
 ('bridge','Button/pop-and-jump-game-2.mp3',.38),
 ('portal','9 Pixel Heroes_SFX/Teleport In.wav',.5),
 ('portalout','9 Pixel Heroes_SFX/Retro Game Teleport 1.wav',.55),
 ('reward','Button/Coins Reward.mp3',.6),
 ('success','Button/Positive Success 1.mp3',.6)]
reports=[]
for kind,rel,maximum in choices:
 path=base/rel
 if not path.exists(): continue
 x=np.frombuffer(subprocess.run([ffmpeg,'-v','error','-i',str(path),'-vn','-ac','2','-ar','48000','-f','f32le','pipe:1'],capture_output=True,check=True).stdout,dtype='<f4').reshape(-1,2)
 amplitude=np.max(np.abs(x),axis=1)
 active=np.flatnonzero(amplitude>10**(-38/20))
 offset=max(0,active[0]/48000-.004)
 duration=min(maximum,(active[-1]+1)/48000-offset+.035,len(x)/48000-offset)
 cut=x[round(offset*48000):round((offset+duration)*48000)]
 peak=20*math.log10(max(float(np.max(np.abs(cut))),1e-12))
 rms=20*math.log10(max(float(np.sqrt(np.mean(cut**2))),1e-12))
 reports.append(dict(kind=kind,file=str(path),totalDuration=round(len(x)/48000,3),offset=float(offset),duration=float(duration),peak_dbfs=round(peak,2),rms_dbfs=round(rms,2),gain=round(-7-peak,2)))
(root/'.ae-codex/rwd007-library-candidates.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports,indent=2))
