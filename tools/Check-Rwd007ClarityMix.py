import json, math, subprocess, argparse, wave
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--plan', action='store_true')
parser.add_argument('--music-db', type=float)
args=parser.parse_args()
data=json.loads((root/'.ae-codex/rwd007-clarity-audio-metadata.json').read_text(encoding='utf-8-sig'))
rate=48000
ffmpeg=r'C:\Users\nguye\AppData\Local\XGetter\externals\ffmpeg.exe'
sources={}
def decode(path):
    if path not in sources:
        pcm=subprocess.run([ffmpeg,'-v','error','-i',path,'-vn','-ac','2','-ar',str(rate),'-f','f32le','pipe:1'],capture_output=True,check=True).stdout
        sources[path]=np.frombuffer(pcm,dtype='<f4').reshape(-1,2)
    return sources[path]
def db(x): return round(20*math.log10(max(float(np.max(np.abs(x))),1e-12)),2)
reports=[]
for comp in data['comps']:
    mix=np.zeros((round(comp['duration']*rate),2),dtype=np.float64)
    music=np.zeros_like(mix);sfx=np.zeros_like(mix)
    eventreports=[]
    cues=list(comp['cues'])
    if args.plan:
        assets={r['kind']:r for r in json.loads((root/'.ae-codex/rwd007-element-sound-assets.json').read_text(encoding='utf-8'))}
        prefix='GAME SFX | ' if comp['duration']==30 else 'COMP1 SFX | '
        for trigger,kind,label in [('BRIDGE pass','bridge','BRIDGE TOP'),('LOWER BRIDGE','bridge','BRIDGE BOTTOM'),('ONE WAY GATE','gate','ONE WAY GATE'),('DELIVERY TURN','gate','DELIVERY TURN')]:
            original=next(c for c in cues if c['name']==prefix+trigger)
            asset=assets[kind];a=original['start'];b=a+asset['duration'];gain=asset['gain']
            cues.append(dict(name='RWD007 ELEMENT SFX | '+label,file=asset['file'],start=a,end=b,offset=asset['offset'],sourceId=0,
                             levels=[[0,[-55,-55]],[.006,[gain,gain]],[asset['duration']-.05,[gain,gain]],[asset['duration'],[-55,-55]]]))
    for cue in cues:
        src=decode(cue['file']);a=round(cue['start']*rate);off=round(cue['offset']*rate)
        n=min(round((cue['end']-cue['start'])*rate),len(mix)-a,len(src)-off)
        if n<=0 or off<0: raise RuntimeError('Source bounds '+cue['name'])
        ts=np.arange(n)/rate;env=np.asarray([[r[0],*r[1]] for r in cue['levels']]);is_music=cue['sourceId']==2367
        delta=0
        if args.plan:
            if is_music: delta=-18
            elif cue['name'].startswith(('GAME SFX | ','COMP1 SFX | ')): delta=1 if cue['offset']>15 else 5
            elif cue['name'].startswith('COMBO POP | '): delta=6
            elif cue['name'].startswith('RWD007 SFX | '):
                if 'tap ' in cue['name']:delta=8
                elif 'portal ' in cue['name']:delta=12
                elif 'filled grid' in cue['name']:delta=7
                else:delta=5
        if is_music and args.music_db is not None:
            absolute=ts+cue['start']
            tail=np.clip((absolute-(comp['duration']-.25))/.25,0,1)
            music_level=args.music_db-30*tail*tail*(3-2*tail)
            gain=np.column_stack([10**(music_level/20),10**(music_level/20)])
        else:
            gain=np.column_stack([10**((np.interp(ts,env[:,0],env[:,ch+1])+delta)/20) for ch in range(2)])
        sig=src[off:off+n]*gain;mix[a:a+n]+=sig
        if is_music:music[a:a+n]+=sig
        elif not cue['name'].startswith(('VOICE | ','OUTRO','SOUND OUTRO')):
            sfx[a:a+n]+=sig
            eventreports.append(dict(name=cue['name'],time=cue['start'],peak_dbfs=db(sig)))
    reports.append(dict(comp=comp['name'],peak_dbfs=db(mix),clipped_samples=int(np.sum(np.abs(mix)>=1)),music_peak_dbfs=db(music),sfx_peak_dbfs=db(sfx),events=eventreports))
out=root/'.ae-codex'/('rwd007-music-minus10-planned-mix.json' if args.music_db is not None else ('rwd007-clarity-planned-mix.json' if args.plan else 'rwd007-clarity-mix-check.json'))
out.write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='events'} for r in reports],indent=2))
if any(r['clipped_samples'] for r in reports): raise RuntimeError('Mix clips')
