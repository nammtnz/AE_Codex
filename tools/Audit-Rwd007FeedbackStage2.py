from pathlib import Path
from array import array
import io, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
FF = r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
MOVIE = r'E:/Task/Snacky Dash/RWD_VD007/FT/Movie_012.mp4'
START = -33.2266666666667
STRETCH = .6
INSPECT = ROOT / '.ae-codex/inspection/rwd007-feedback-stage2'
ASSETS = ROOT / 'assets/rwd007-feedback'
INSPECT.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)

def run(args):
    return subprocess.run([FF, '-v', 'error'] + args, capture_output=True, check=True).stdout

def frame(root_time):
    source_time = (root_time-START)/STRETCH
    data = run(['-ss', str(source_time), '-i', MOVIE, '-frames:v', '1', '-vf', 'scale=216:384', '-f', 'image2pipe', '-vcodec', 'png', 'pipe:1'])
    return Image.open(io.BytesIO(data)).convert('RGB')

times = [round(12.4+i*.2, 4) for i in range(49)]
cols, cellw, cellh = 7, 216, 409
sheet = Image.new('RGB', (cols*cellw, math.ceil(len(times)/cols)*cellh), '#222222')
draw = ImageDraw.Draw(sheet)
for i,t in enumerate(times):
    im = frame(t)
    x,y = (i%cols)*cellw,(i//cols)*cellh
    sheet.paste(im,(x,y+25))
    draw.text((x+5,y+5),f'root {t:.2f}s | src {(t-START)/STRETCH:.3f}s',fill='white')
sheet.save(INSPECT/'overview.jpg', quality=95)

# Candidate preparation keeps all source audio unchanged. Each asset is natural speed,
# has leading silence removed, a soft attack and tail, and a reproducible peak level.
candidates = [
    ('block-collect',r'E:/Audio/SFX/Cartoon/8 Epic Garden_SFX/hit/Arcade Collect Hit 02.mp3',.18,6500,-10,.003,.025),
    ('tray-launch',r'E:/Audio/SFX/Cartoon/Button/pop-and-jump-game-2.mp3',.28,7000,-7,.004,.055),
    ('reward-disappear',r'E:/Audio/SFX/Cartoon/Button/Coins Reward.mp3',.55,7000,-6.5,.006,.07),
]
report=[]
for kind,path,maximum,cutoff,target,attack,tail in candidates:
    raw=run(['-i',path,'-vn','-ac','2','-ar','48000','-f','f32le','pipe:1'])
    x=np.frombuffer(raw,dtype='<f4').reshape(-1,2)
    amplitude=np.max(np.abs(x),axis=1)
    active=np.flatnonzero(amplitude>10**(-38/20))
    if len(active)==0: raise ValueError('Silent source '+path)
    offset=max(0,float(active[0])/48000-.004)
    duration=min(maximum, len(x)/48000-offset)
    filt=f'atrim=start={offset}:duration={duration},asetpts=PTS-STARTPTS,highpass=f=100,lowpass=f={cutoff},afade=t=in:st=0:d={attack},afade=t=out:st={duration-tail}:d={tail}'
    raw=run(['-i',path,'-vn','-af',filt,'-ac','2','-ar','48000','-f','f32le','pipe:1'])
    x=np.frombuffer(raw,dtype='<f4')
    peak=float(np.max(np.abs(x)))
    gain=10**(target/20)/peak
    pcm=np.rint(np.clip(x*gain,-.999,.999)*32767).astype('<i2')
    output=ASSETS/(kind+'.wav')
    with wave.open(str(output),'wb') as w:
        w.setnchannels(2);w.setsampwidth(2);w.setframerate(48000);w.writeframes(pcm.tobytes())
    report.append(dict(kind=kind,source=path,path=str(output).replace('\\','/'),offset=offset,duration=len(x)/96000,peak_dbfs=target,cutoff=cutoff,attack=attack,tail=tail,source_filtered_peak=20*math.log10(peak),rms_dbfs=20*math.log10(max(float(np.sqrt(np.mean((x*gain)**2))),1e-12))))

source_start=(12.3666666666667-START)/STRETCH
raw=run(['-ss',str(source_start),'-i',MOVIE,'-t','16.05556','-vn','-ac','1','-ar','48000','-f','f32le','pipe:1'])
x=np.frombuffer(raw,dtype='<f4')
windows=[]
for i in range(0,len(x)-480,480):
    chunk=x[i:i+480]
    windows.append(dict(root=12.3666666666667+i/48000*STRETCH,peak=float(np.max(np.abs(chunk))),rms=float(np.sqrt(np.mean(chunk**2)))))
(ROOT/'.ae-codex/rwd007-feedback-stage2-audio-envelope.json').write_text(json.dumps(windows),encoding='utf-8')
(ROOT/'.ae-codex/rwd007-feedback-audio-assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(overview=str(INSPECT/'overview.jpg'),assets=report),indent=2))
