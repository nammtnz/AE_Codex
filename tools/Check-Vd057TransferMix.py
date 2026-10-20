import json,subprocess,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1];p=json.loads((root/'.ae-codex/vd057-transfer-result.json').read_text(encoding='utf-8-sig'));plan=json.loads((root/'.ae-codex/vd057-transfer-plan.json').read_text())
ff=r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe';rate=24000;cache={}
def decode(path):
 if path not in cache:
  raw=subprocess.run([ff,'-v','error','-i',path,'-vn','-ac','2','-ar',str(rate),'-f','f32le','pipe:1'],capture_output=True,check=True).stdout
  cache[path]=np.frombuffer(raw,dtype='<f4').reshape(-1,2)
 return cache[path]
mix=np.zeros((round(p['duration']*rate),2));sfx=np.zeros_like(mix);levels=[]
for c in p['sounds']:
 a=round(c['time']*rate);off=round(c['offset']*rate);n=round(c['duration']*rate);sig=decode(c['file'])[off:off+n];n=min(n,len(sig),len(mix)-a);t=np.arange(n)/rate
 db=np.interp(t,[0,.005,c['duration']-.025,c['duration']],[-60,c['gain'],c['gain'],-60]);v=sig[:n]*10**(db[:,None]/20);sfx[a:a+n]+=v;levels.append(dict(kind=c['kind'],time=c['time'],peak=round(20*math.log10(max(float(abs(v).max()),1e-10)),2)))
# The bed's actual duck can only lower this conservative peak-bound mix.
music=decode(plan['music']['file'])[:len(mix)]*10**(-26/20);mix[:len(music)]+=music;mix+=sfx
peak=float(abs(mix).max());report=dict(peakUpperBoundDbfs=round(20*math.log10(peak),2),clippedSamples=int((abs(mix)>=1).sum()),cues=len(levels),levels=levels)
(root/'.ae-codex/vd057-transfer-audio-check.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='levels'}))
folder=root/'.ae-codex/inspection/vd057-orange-tile-fix';fs=sorted(folder.glob('tap*.png'),key=lambda f:int(f.stem[3:]));sheet=Image.new('RGB',(270*5,500*2));d=ImageDraw.Draw(sheet)
for i,f in enumerate(fs):sheet.paste(Image.open(f).convert('RGB').resize((270,480)),(i%5*270,i//5*500));d.text((i%5*270,i//5*500+480),f.stem,fill='white')
sheet.save(folder/'sheet.png')
