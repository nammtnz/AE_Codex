from pathlib import Path
from PIL import Image,ImageDraw
import json,sys
root=Path(sys.argv[1]);rows=json.loads((root/'verification-frames.json').read_text());ids=list(dict.fromkeys(s['compId'] for s in rows))
for batch in range(2):
 sheet=Image.new('RGB',(1200,1000),'#252525');d=ImageDraw.Draw(sheet)
 for row,cid in enumerate(ids[batch*4:batch*4+4]):
  shots=[s for s in rows if s['compId']==cid]
  for col,s in enumerate(shots):
   im=Image.open(root/s['file']).convert('RGB');x,y=s['x'],s['y'];im=im.crop((x-90,y-100,x+200,y+145)).resize((300,225));sheet.paste(im,(col*300,row*250+25));d.text((col*300+4,row*250+3),s['name']+' t='+str(round(s['time'],3)),fill='white')
 sheet.save(root/f'final-contact-review-{batch}.jpg')
print('Contact review sheets ready')
