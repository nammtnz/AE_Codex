import json, math, subprocess
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1];base=Path('E:/Audio/SFX/Cartoon')
ffmpeg=r'C:\Users\nguye\AppData\Local\XGetter\externals\ffmpeg.exe'
choices=[('victory','10 Empire Warriors/sfx_ui_victory.mp3',1),('levelup','Level Up _ Open Chest/level-up-2-28FQTHB/Level Up 2.wav',1),('soft','Level Up _ Open Chest/soft-level-up-UEBDRG7/Soft Level Up.wav',1),('coins','Coins/win game level 209 - coins.wav',1),('fireworks','RTFX/Explosion/SFX - Explosion 01 Fireworks Impact.mp3',.4),('sparkles','RTFX/Sparks/SFX - Sparks 01 Fireworks.mp3',.65),('fireworks2','RTFX/Explosion/SFX - Explosion 04 Fireworks Sparks.mp3',.4)]
reports=[]
for kind,rel,maximum in choices:
 path=base/rel
 if not path.exists():continue
 x=np.frombuffer(subprocess.run([ffmpeg,'-v','error','-i',str(path),'-vn','-ac','2','-ar','48000','-f','f32le','pipe:1'],capture_output=True,check=True).stdout,dtype='<f4').reshape(-1,2)
 active=np.flatnonzero(np.max(np.abs(x),axis=1)>10**(-38/20));offset=max(0,active[0]/48000-.004);duration=min(maximum,len(x)/48000-offset)
 cut=x[round(offset*48000):round((offset+duration)*48000)];peak=20*math.log10(max(float(np.max(np.abs(cut))),1e-12));rms=20*math.log10(max(float(np.sqrt(np.mean(cut**2))),1e-12))
 reports.append(dict(kind=kind,file=str(path),totalDuration=round(len(x)/48000,3),offset=float(offset),duration=float(duration),peak_dbfs=round(peak,2),rms_dbfs=round(rms,2),gain=round((-8 if kind in ['victory','levelup','soft','coins'] else -12)-peak,2)))
(root/'.ae-codex/rwd007-win-sound-assets.json').write_text(json.dumps(reports,indent=2),encoding='utf-8');print(json.dumps(reports,indent=2))
