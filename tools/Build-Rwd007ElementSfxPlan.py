import json, re, math, subprocess
from pathlib import Path
import numpy as np

root=Path(__file__).resolve().parents[1]
metadata=json.loads((root/'.ae-codex/rwd007-clarity-audio-metadata.json').read_text(encoding='utf-8-sig'))
assets={x['kind']:x for x in json.loads((root/'.ae-codex/rwd007-library-candidates.json').read_text(encoding='utf-8'))}
audit=(root/'.ae-codex/rwd007-element-cue-times.txt').read_text(encoding='utf-8-sig')
rate=48000
ffmpeg=r'C:\Users\nguye\AppData\Local\XGetter\externals\ffmpeg.exe'
cache={}
def decode(path):
    if path not in cache:
        raw=subprocess.run([ffmpeg,'-v','error','-i',path,'-vn','-ac','2','-ar',str(rate),'-f','f32le','pipe:1'],capture_output=True,check=True).stdout
        cache[path]=np.frombuffer(raw,dtype='<f4').reshape(-1,2)
    return cache[path]
def db(sig):return round(20*math.log10(max(float(np.max(np.abs(sig))),1e-12)),2)
def duck(times,spans,amount,before=.05,after=.13):
    out=np.zeros_like(times)
    for a,b in spans:
        x=np.clip((times-(a-before))/before,0,1)
        y=np.clip((times-b)/after,0,1)
        env=amount*x*x*(3-2*x)*(1-y*y*(3-2*y))
        out=np.maximum(out,env)
    return out
def levels(cue):
    times=np.arange(round((cue['end']-cue['start'])*rate))/rate
    env=np.asarray([[r[0],*r[1]] for r in cue['levels']])
    return times,np.column_stack([np.interp(times,env[:,0],env[:,ch+1]) for ch in range(2)])
def new_cue(name,time,kind,peak=-7,duration=None):
    a=assets[kind];dur=duration or a['duration'];gain=round(peak-a['peak_dbfs'],2)
    return dict(name=name,file=a['file'],start=time,end=time+dur,offset=a['offset'],sourceId=0,gain=gain,
                levels=[[0,[-55,-55]],[.004,[gain,gain]],[max(.004,dur-.06),[gain,gain]],[dur,[-55,-55]]])
plans=[];reports=[]
for comp in metadata['comps']:
    cues=json.loads(json.dumps(comp['cues']));short=comp['duration']==15
    visualid=comp['id'] if short else (1926 if comp['id']==671 else 2003)
    section=audit.split('COMP '+str(visualid)+' ')[1].split('COMP ')[0]
    factor=1 if short else 2.25
    voices=[[c['start'],c['end']] for c in cues if c['name'].startswith('VOICE | filled ')]
    changes=[];added=[]
    def replace(cue,kind,peak=-7,duration=None):
        new=new_cue(cue['name'],cue['start'],kind,peak,duration)
        changes.append(dict(id=cue['id'],name=cue['name'],action='replace',expectedStart=cue['start'],expectedEnd=cue['end'],expectedOffset=cue['offset'],**{k:new[k] for k in ['file','start','end','offset','gain']}))
        cue.update(new);cue['voiceDuck']=3
    def boost(cue,amount):
        changes.append(dict(id=cue['id'],name=cue['name'],action='boost',delta=amount,expectedStart=cue['start'],expectedEnd=cue['end'],expectedOffset=cue['offset']))
        cue['levels']=[[t,[v+amount if v>-40 else v for v in vs]] for t,vs in cue['levels']]
    for cue in cues:
        name=cue['name']
        if name=='RWD007 ELEMENT SFX | ONE WAY GATE': replace(cue,'startup',-6.5,.85 if not short else .5)
        elif name.startswith('RWD007 ELEMENT SFX | BRIDGE'): boost(cue,4)
        elif name=='RWD007 ELEMENT SFX | DELIVERY TURN': boost(cue,4)
        elif name.startswith('RWD007 SFX | tap '): boost(cue,3)
        elif name.startswith('COMBO POP | '): boost(cue,2)
        elif name.startswith('RWD007 SFX | filled grid '):replace(cue,'reward' if 'EPIC' in name else 'success',-7,.6)
        elif name=='RWD007 SFX | portal enter':replace(cue,'portal',-7,.5)
        elif name=='RWD007 SFX | portal exit':replace(cue,'portalout',-7,.55)
        elif name.startswith('RWD007 SFX | zoom out ') or name=='RWD007 SFX | outro reveal':boost(cue,3)
    for layer in re.split(r'(?=LAYER )',section)[1:]:
        header=layer.splitlines()[0]
        if 'enabled=true' not in header:continue
        if 'ARROW GLYPH FX | ' in header:
            label=re.search(r'ARROW GLYPH FX \| (.*?) enabled=',header)[1].upper()
            spans=json.loads(re.search(r'var spans=(\[[^;]+);',layer)[1])
            for number,(a,b) in enumerate(spans,1):
                added.append(new_cue('RWD007 ELEMENT SFX | DIRECTION '+label+' '+str(number),a*factor,'select',-8,.16))
        elif 'PIXEL BORDER FX | BRIDGE ' in header and 'upper rim' in header:
            label='TOP' if 'BRIDGE TOP' in header else 'BOTTOM'
            opacity=re.search(r'transform/Opacity[^\n]*(?:\n  [^\n]*)*',layer)[0]
            keys=[(float(t),float(v)) for t,v in re.findall(r'\n  ([0-9.]+)=([0-9.]+)',opacity)]
            times=[t*factor for (pt,pv),(t,v) in zip(keys,keys[1:]) if pv==0 and v>0]
            existing=next(c for c in cues if c['name']=='RWD007 ELEMENT SFX | BRIDGE '+label)
            for number,time in enumerate(times,1):
                if abs(time-existing['start'])<.05:continue
                added.append(new_cue('RWD007 ELEMENT SFX | BRIDGE '+label+' EXTRA '+str(number),time,'bridge',-8,.28))
    # Gate selection is hand contact 10, while the last glow key is train passage.
    added.append(new_cue('RWD007 ELEMENT SFX | GATE ELECTRIC SELECT',7.6 if short else 17.1,'impact',-6.5,.35))
    added.append(new_cue('RWD007 ELEMENT SFX | GATE ELECTRIC PASS',8.03333333333333*factor,'zap',-7,.35))
    for cue in added:cue['voiceDuck']=3
    allcues=cues+added
    events=[[c['start'],c['end']] for c in allcues if c['name'].startswith(('RWD007 ','COMBO POP | ','GAME SFX | ','COMP1 SFX | '))]
    mix=np.zeros((round(comp['duration']*rate),2));music=np.zeros_like(mix);sfx=np.zeros_like(mix);eventreports=[]
    for cue in allcues:
        ts,env=levels(cue);absolute=ts+cue['start']
        if cue['sourceId']==2367:
            newenv=-20-duck(absolute,events,6,.06,.18)-duck(absolute,voices,7,.06,.18)
            tail=np.clip((absolute-(comp['duration']-.25))/.25,0,1);newenv-=30*tail*tail*(3-2*tail)
            env=np.column_stack([newenv,newenv])
        if cue.get('voiceDuck'):env-=duck(absolute,voices,cue['voiceDuck'],.05,.12)[:,None]
        src=decode(cue['file']);off=round(cue['offset']*rate);start=round(cue['start']*rate)
        n=min(len(env),len(src)-off,len(mix)-start)
        if n<=0 or off<0:raise RuntimeError(cue['name'])
        signal=src[off:off+n]*10**(env[:n]/20);mix[start:start+n]+=signal
        if cue['sourceId']==2367:music[start:start+n]+=signal
        elif not cue['name'].startswith(('VOICE | ','OUTRO','SOUND OUTRO')):
            sfx[start:start+n]+=signal
            if cue['name'].startswith('RWD007 ELEMENT') or any(c['id']==cue.get('id') for c in changes):eventreports.append(dict(name=cue['name'],time=cue['start'],peak_dbfs=db(signal)))
    report=dict(comp=comp['name'],peak_dbfs=db(mix),clipped_samples=int(np.sum(np.abs(mix)>=1)),music_peak_dbfs=db(music),sfx_peak_dbfs=db(sfx),added=len(added),events=eventreports)
    reports.append(report)
    plans.append(dict(id=comp['id'],name=comp['name'],duration=comp['duration'],visualid=visualid,musicId=next(c['id'] for c in cues if c['sourceId']==2367),changes=changes,added=added,events=events,voices=voices))
(root/'.ae-codex/rwd007-element-sfx-plan.json').write_text(json.dumps(dict(comps=plans),indent=2),encoding='utf-8')
(root/'.ae-codex/rwd007-element-sfx-planned-mix.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps([{k:v for k,v in r.items() if k!='events'} for r in reports],indent=2))
if any(r['clipped_samples'] or r['peak_dbfs']>-1.5 for r in reports):raise RuntimeError('Plan needs more headroom')
