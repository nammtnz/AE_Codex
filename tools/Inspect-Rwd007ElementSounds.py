import subprocess,json,math
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
ffmpeg=r'C:\Users\nguye\AppData\Local\XGetter\externals\ffmpeg.exe'
files={'bridge':r'E:\Audio\SFX\Cartoon\Button\pop-and-jump-game-2.mp3',
       'gate':r'E:\Audio\SFX\Cartoon\Button\sfx_ui_select.mp3'}
out=[]
for kind,path in files.items():
    pcm=subprocess.run([ffmpeg,'-v','error','-i',path,'-vn','-ac','2','-ar','48000','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
    x=np.frombuffer(pcm,dtype='<f4').reshape(-1,2)
    active=np.flatnonzero(np.max(np.abs(x),axis=1)>10**(-40/20))
    if not len(active):raise RuntimeError('Silent '+path)
    offset=max(0,float(active[0])/48000-.006)
    duration=min(.38 if kind=='bridge' else .24,len(x)/48000-offset)
    cut=x[round(offset*48000):round((offset+duration)*48000)]
    peak=float(np.max(np.abs(cut)))
    db=20*math.log10(max(peak,1e-12))
    out.append(dict(kind=kind,file=path,totalDuration=len(x)/48000,offset=offset,duration=duration,peak_dbfs=db,gain=round((-11 if kind=='bridge' else -12)-db,2)))
(root/'.ae-codex/rwd007-element-sound-assets.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out,indent=2))
