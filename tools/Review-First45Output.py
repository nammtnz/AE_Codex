import json, math
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

root = Path(__file__).resolve().parents[1]
plan_path = root / '.ae-codex/inspection/source-first45/first45-hand-plan.json'
plan = json.loads(plan_path.read_text(encoding='utf-8-sig'))
changes = []
for event in plan['events'][1:]:
    close = [r for r in plan['track'] if event['arrival']-1.25 <= r['t'] <= event['arrival'] and math.hypot(r['x']-event['point'][0],r['y']-event['point'][1])<65]
    if not close:
        raise ValueError(f'No approach sample: {event}')
    first = close[0]['t']
    old = event['t']
    event['firstApproach'] = first
    event['t'] = round(min(old,first-.35),3)
    if event['t'] != old:
        changes.append({'old':old,'new':event['t'],'approach':first,'point':event['point']})
out_path = plan_path.with_name('first45-hand-plan-before-arrival.json')
out_path.write_text(json.dumps(plan,indent=2),encoding='utf-8')
print(json.dumps({'earlierClicks':changes,'plan':str(out_path)}))

folder = root / '.ae-codex/inspection/20261012-174958-dbe2fbea'
stats = []
for file in sorted(folder.glob('*.png')):
    with Image.open(file) as im:
        a=np.asarray(im.convert('RGB'))
        stats.append({'frame':file.name,'mean':round(float(a.mean()),2),'blackPct':round(float((a.max(axis=2)<12).mean()*100),4)})
(folder/'frame-stats.json').write_text(json.dumps(stats,indent=2),encoding='utf-8')
print(json.dumps({'frames':len(stats),'blackFrames':[r for r in stats if r['blackPct']>85],'maxBlackPct':max(r['blackPct'] for r in stats)}))
times=['0.0000','2.8667','5.0000','10.0000','15.0000','20.0000','25.4000','25.5400','26.0500','27.3600','27.5000','28.0000','32.0000','38.0000','41.9000','42.0000','42.2000','42.3500','43.0000','44.9667']
for cid,wh in [(811,(480,270)),(671,(180,320))]:
    cw,ch=wh
    montage=Image.new('RGB',(cw*4,(ch+27)*5),'#202020')
    draw=ImageDraw.Draw(montage)
    for index,t in enumerate(times):
        file=folder/f'c{cid}-t{t}.png'
        with Image.open(file) as im:
            im=im.convert('RGB');im.thumbnail((cw,ch))
            x=(index%4)*cw;y=(index//4)*(ch+27)
            montage.paste(im,(x,y+27));draw.text((x+6,y+6),f'{cid} - {t}s',fill='white')
    montage.save(folder/f'review-{cid}.jpg',quality=92)
