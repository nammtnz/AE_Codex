from pathlib import Path
from array import array
import subprocess, math, json, wave
root=Path(__file__).resolve().parents[1]
out=root/'assets/rwd007-asmr'
out.mkdir(exist_ok=True)
ff=r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
sources=[
 ('tap-pop',r'E:/Audio/SFX/Cartoon/Button/cartoon-pop.mp3',.0233125,.1073125,7300,-11.5,.004,.016),
 ('tap-click',r'E:/Audio/SFX/Cartoon/Button/interface-pack/Click.wav',None,.17,6500,-12,.004,.02),
 ('portal-in',r'E:/Audio/SFX/Cartoon/9 Pixel Heroes_SFX/___Export/General/sfx_general_teleport_in.mp3',.0470208,.55,4700,-12.5,.015,.075),
 ('portal-out',r'E:/Audio/SFX/Cartoon/9 Pixel Heroes_SFX/___Export/General/sfx_general_teleport_out.mp3',.0455208,.38,5600,-12.5,.006,.055),
]
result=[]
for kind,path,offset,duration,cutoff,target,attack,tail in sources:
 raw=subprocess.run([ff,'-v','error','-i',path,'-vn','-ac','2','-ar','48000','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
 samples=array('f');samples.frombytes(raw)
 if offset is None:
  first=next(i for i in range(0,len(samples),2) if max(abs(samples[i]),abs(samples[i+1]))>10**(-38/20))
  offset=max(0,first/96000-.003)
 duration=min(duration,len(samples)/96000-offset)
 filt=f'atrim=start={offset}:duration={duration},asetpts=PTS-STARTPTS,highpass=f=100,lowpass=f={cutoff},afade=t=in:st=0:d={attack},afade=t=out:st={duration-tail}:d={tail}'
 raw=subprocess.run([ff,'-v','error','-i',path,'-af',filt,'-vn','-ac','2','-ar','48000','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
 samples=array('f');samples.frombytes(raw)
 peak=max(abs(x) for x in samples)
 gain=10**(target/20)/peak
 pcm=array('h',(round(max(-.999,min(.999,x*gain))*32767) for x in samples))
 output=out/(kind+'-asmr.wav')
 with wave.open(str(output),'wb') as w:w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm.tobytes())
 result.append(dict(kind=kind,source=path,path=str(output).replace('\\','/'),offset=offset,duration=len(samples)/96000,source_filtered_peak=20*math.log10(peak),peak_dbfs=target,cutoff=cutoff,attack=attack,tail=tail))
(root/'.ae-codex/rwd007-asmr-assets.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
