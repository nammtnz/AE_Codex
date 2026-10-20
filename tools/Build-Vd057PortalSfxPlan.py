from pathlib import Path
import json, math, subprocess, wave, copy
import numpy as np

ROOT=Path('C:/Users/nguye/AE_Codex')
FF=str(ROOT/'.ae-codex/praise-runtime-20261016/imageio_ffmpeg/binaries/ffmpeg-win-x86_64-v7.1.exe')
RATE=48000
live=json.loads((ROOT/'.ae-codex/vd057-portal-sfx-live.json').read_text(encoding='utf-8-sig'))
prepared=json.loads((ROOT/'.ae-codex/vd057-portal-sfx-assets.json').read_text(encoding='utf-8-sig'))
ready=ROOT/'assets/vd057-portal-sfx/ready'
review=ROOT/'assets/vd057-portal-sfx/review'
review.mkdir(parents=True,exist_ok=True)

def new(kind,gate,filename,start,end,env,right=-1.5):
    path=ready/filename
    if not path.exists():raise RuntimeError(f'Missing prepared SFX {path}')
    return dict(name=f'VD057 PORTAL FX SFX | {gate} | {kind}',kind=kind,gate=gate,file=str(path),startTime=start,inPoint=start,outPoint=end,stretch=100,levelsKeys=[dict(time=t,value=[gain,gain+right]) for t,gain in env])

layers=[
new('VORTEX LOOP','LOWER','vortex-bed.wav',0,319/30,[(0,-60),(.15,-23),(.6,-22),(8.6,-22),(8.93,-19),(9.13,-17),(9.47,-23),(10.3,-24),(319/30,-60)]),
new('INWARD WIND','LOWER','inward-wind-bed.wav',0,319/30,[(0,-60),(.3,-24),(8.6,-22),(8.97,-15),(9.13,-14.5),(9.45,-23),(10.2,-24),(319/30,-60)]),
new('TRAIN SUCTION','LOWER','train-suction.wav',8.83333333333333,8.83333333333333+.64,[(8.83333333333333,-60),(8.87,-14),(9.0333333333333,-7),(9.18,-7),(9.38,-14),(8.83333333333333+.64,-60)],-1),
new('AIR CLOSE','LOWER','portal-air-close.wav',10.3,319/30,[(10.3,-60),(10.33,-16),(10.5,-12),(10.6,-16),(319/30,-60)]),
new('VORTEX LOOP','UPPER LEFT','vortex-bed.wav',319/30,12,[(319/30,-60),(10.7,-22),(10.93,-18),(11.2,-22),(11.75,-24),(12,-60)],-3),
new('INWARD WIND','UPPER LEFT','inward-wind-bed.wav',319/30,12,[(319/30,-60),(10.7,-22),(10.93,-17),(11.27,-21),(11.75,-25),(12,-60)],-3),
new('TELEPORT AIR PULL','UPPER LEFT','train-suction.wav',319/30,319/30+.64,[(319/30,-60),(10.68,-17),(10.83,-13),(11,-13),(11.19,-22),(319/30+.64,-60)],-3),
new('AIR CLOSE','UPPER LEFT','portal-air-close.wav',350/30,12,[(350/30,-60),(11.7,-16),(356/30,-12),(11.96,-16),(12,-60)],-3),
]
edits=[]
for lid,onset,duck in [(5968,271/30,3),(5971,269/30,4)]:
    before=next(l for l in live['audio'] if l['id']==lid)
    delta=onset-before['inPoint']
    after=copy.deepcopy(before)
    for key in ('inPoint','outPoint','startTime'):after[key]+=delta
    after['levelsKeys']=[dict(k,time=k['time']+delta,value=[v-duck if v>-59 else v for v in k['value']]) for k in before['levelsKeys']]
    after['samples']=[]
    edits.append(dict(id=lid,delta=delta,duckDb=duck,before=before,after=after))

cache={}
def read(path):
    key=path.lower().replace('\\','/')
    if key not in cache:
        r=subprocess.run([FF,'-v','error','-i',path,'-vn','-ar',str(RATE),'-ac','2','-f','f32le','pipe:1'],capture_output=True,check=True)
        cache[key]=np.frombuffer(r.stdout,dtype='<f4').reshape(-1,2).astype('float64')
    return cache[key]
def db(x):return round(20*math.log10(max(float(x),1e-12)),3)
def render(rows):
    ts=np.arange(13*RATE)/RATE
    mix=np.zeros((len(ts),2))
    for layer in rows:
        if layer['outPoint']<=0 or layer['inPoint']>=13:continue
        if not layer.get('audioEnabled',True):continue
        if not layer['file']:raise RuntimeError('Nested audio requires explicit reconstruction')
        src=read(layer['file']);idx=(ts-layer['startTime'])/(layer['stretch']/100)*RATE
        valid=np.flatnonzero((ts>=layer['inPoint'])&(ts<layer['outPoint'])&(idx>=0)&(idx<len(src)-1))
        if not len(valid):continue
        si=idx[valid];lo=np.floor(si).astype('int64');fraction=si-lo
        sig=src[lo]*(1-fraction[:,None])+src[lo+1]*fraction[:,None]
        if layer.get('expression'):
            samples=layer['samples'];times=[s['time'] for s in samples];vals=np.array([s['gain'] for s in samples])
        elif layer.get('levelsKeys'):
            samples=layer['levelsKeys'];times=[s['time'] for s in samples];vals=np.array([s['value'] for s in samples])
        else:
            times=[0];vals=np.array([layer['levelsValue']])
        gain=np.column_stack([np.interp(ts[valid],times,vals[:,c]) for c in (0,1)])
        mix[valid]+=sig*np.power(10,gain/20)
    return mix
original=[l for l in live['audio'] if l['audioEnabled']]
changed={e['id']:e['after'] for e in edits}
baseline=render(original)
adjusted=render([changed.get(l['id'],l) for l in original])
added=render(layers)
mixed=adjusted+added
def truepeak(sig):
    r=subprocess.run([FF,'-v','error','-f','f32le','-ar',str(RATE),'-ac','2','-i','pipe:0','-af','aresample=192000','-f','f32le','pipe:1'],input=sig.astype('<f4').tobytes(),capture_output=True,check=True)
    return db(abs(np.frombuffer(r.stdout,dtype='<f4')).max())
def metrics(sig):return dict(samplePeakDbfs=db(abs(sig).max()),truePeak4xDbfs=truepeak(sig),clippedSamples=int((abs(sig)>=1).sum()),rmsDbfs=db(np.sqrt((sig**2).mean())))
def save(name,sig):
    path=review/name
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2);f.setsampwidth(3);f.setframerate(RATE)
        ints=np.round(np.clip(sig,-1,1-1/8388608)*8388607).astype('<i4')
        f.writeframes(ints.view('uint8').reshape(-1,4)[:,:3].tobytes())
    return str(path)
windows=[]
for label,start,end in [('loop',0,8.7),('lower suction',8.7,9.7),('lower close',10.2,10.63333333333),('upper portal',10.63333333333,12),('post portal',12,13)]:
    sl=slice(round(start*RATE),round(end*RATE));windows.append(dict(label=label,start=start,end=end,original=metrics(baseline[sl]),newSfx=metrics(added[sl]),mix=metrics(mixed[sl])))
report=dict(state='ready' if abs(mixed).max()<.89 else 'review-needed',preflightRunId=live['runId'],compId=live['comp']['id'],newLayers=layers,existingEdits=edits,newAudio=metrics(added),mix=metrics(mixed),original=metrics(baseline),windows=windows,preparedAssetsFile='.ae-codex/vd057-portal-sfx-assets.json',previewFile=save('vd057-portal-mix-0-13s.wav',mixed),sfxOnlyFile=save('vd057-portal-sfx-only-0-12s.wav',added[:12*RATE]),limitations=['Offline reconstruction, not an AE render or an auditory verification. Audio input is unsupported in the current tool session.','Existing music expressions sampled from live AE every10ms; other existing and proposed gain keys are reconstructed with linear dB interpolation.','No active nested audio, audio effects or solo layers were present at preflight. Only first13s reconstructed because edits end by12s.'])
if report['mix']['truePeak4xDbfs']>=-1:report['state']='review-needed'
(ROOT/'.ae-codex/vd057-portal-sfx-plan.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['state','preflightRunId','newAudio','mix','original','previewFile']},indent=2))
for w in windows:print(json.dumps(w))
