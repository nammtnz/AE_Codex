"""Locate the locomotive's yellow cab, then review marked frames before applying."""
from pathlib import Path
import json, sys, math
import numpy as np
from PIL import Image, ImageDraw

root = Path(sys.argv[1])
samples = json.loads((root / 'samples.json').read_text(encoding='utf-8-sig'))['samples']
samples = [s for s in samples if s['tap'] < 27]
def locate(path):
    im = Image.open(path).convert('RGB')
    factor = 2
    a = np.asarray(im.resize((im.width//factor, im.height//factor)))
    r,g,b = [a[:,:,i].astype(int) for i in range(3)]
    mask=(r>210)&(g>190)&(b<105)&(r-g<65)
    seen=np.zeros(mask.shape,dtype=bool); candidates=[]
    for y,x in zip(*np.nonzero(mask)):
        if seen[y,x]: continue
        stack=[(y,x)]; seen[y,x]=True; points=[]
        while stack:
            cy,cx=stack.pop(); points.append((cy,cx))
            for ny,nx in ((cy-1,cx),(cy+1,cx),(cy,cx-1),(cy,cx+1)):
                if 0<=ny<mask.shape[0] and 0<=nx<mask.shape[1] and mask[ny,nx] and not seen[ny,nx]:
                    seen[ny,nx]=True; stack.append((ny,nx))
        if len(points)<6: continue
        ys,xs=zip(*points); x0,x1=min(xs),max(xs); y0,y1=min(ys),max(ys); w=x1-x0+1; h=y1-y0+1
        if not .7<w/h<1.6 or len(points)/(w*h)<.55: continue
        pad=max(w,h); xa=max(0,x0-pad); xb=min(a.shape[1],x1+pad+1); ya=max(0,y0-pad); yb=min(a.shape[0],y1+pad+1)
        rr=r[ya:yb,xa:xb]; gg=g[ya:yb,xa:xb]; bb=b[ya:yb,xa:xb]
        red=((rr>145)&(gg<135)&(rr>gg*1.45)&(rr>bb*1.2)).sum()
        blue=((bb>130)&(bb>rr*1.3)&(gg>70)).sum()
        score=min(red/(w*h),2)*min(blue/(w*h),2)*len(points)
        if score>.3:candidates.append({'x':float((x0+x1)/2*factor),'y':float((y0+y1)/2*factor),'w':int(w*factor),'h':int(h*factor),'score':round(float(score),2)})
    candidates.sort(key=lambda q:q['score'],reverse=True)
    return candidates

results=[]
for s in samples:
    s=dict(s); s['candidates']=locate(root/s['file']);results.append(s)
(root/'head-candidates.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
ids=sorted(set(s['compId'] for s in results))
for cid in ids:
    frames=[s for s in results if s['compId']==cid and '-s2.' in s['file']]
    sheet=Image.new('RGB',(1280,math.ceil(len(frames)/4)*400),'#222222'); d=ImageDraw.Draw(sheet)
    for n,s in enumerate(frames):
        im=Image.open(root/s['file']).convert('RGB'); draw=ImageDraw.Draw(im)
        for rank,q in enumerate(s['candidates'][:2]):
            x,y=q['x'],q['y'];color='magenta' if rank==0 else 'cyan'
            draw.ellipse((x-16,y-16,x+16,y+16),outline=color,width=4)
        im.thumbnail((315,360));x=(n%4)*320+(320-im.width)//2;y=(n//4)*400+30
        sheet.paste(im,(x,y));d.text(((n%4)*320+5,(n//4)*400+4),f"{s['compName']} event {s['event']} t={s['tap']:.3f} candidates={len(s['candidates'])}",fill='white')
    sheet.save(root/f'review-{cid}.jpg')
    crops=Image.new('RGB',(1000,math.ceil(len(frames)/5)*220),'#222222');cd=ImageDraw.Draw(crops)
    for n,s in enumerate(frames):
        if not s['candidates']:continue
        q=s['candidates'][0];im=Image.open(root/s['file']).convert('RGB');draw=ImageDraw.Draw(im);x,y=q['x'],q['y'];draw.ellipse((x-4,y-4,x+4,y+4),outline='magenta',width=2)
        radius=max(35,int(max(q['w'],q['h'])*1.8));im=im.crop((x-radius,y-radius,x+radius,y+radius)).resize((200,190));crops.paste(im,((n%5)*200,(n//5)*220+25));cd.text(((n%5)*200+3,(n//5)*220+4),f"e{s['event']} t={s['tap']:.3f}",fill='white')
    crops.save(root/f'crops-{cid}.jpg')
print(json.dumps({'frames':len(results),'missing':[s['file'] for s in results if not s['candidates']],'sheets':[f'review-{cid}.jpg' for cid in ids]},ensure_ascii=False))
