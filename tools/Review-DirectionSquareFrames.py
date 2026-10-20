from pathlib import Path
from PIL import Image,ImageDraw
import json,sys,math
root=Path(sys.argv[1]);rows=json.loads((root/'square-verification-frames.json').read_text(encoding='utf-8-sig'))
sheet=Image.new('RGB',(1600,math.ceil(len(rows)/8)*225),'#252525');d=ImageDraw.Draw(sheet)
for n,s in enumerate(rows):
 im=Image.open(root/s['file']).convert('RGB');x=max(120,min(im.width-120,s['x']));y=max(100,min(im.height-150,s['y']));im=im.crop((x-100,y-75,x+140,y+170)).resize((200,200));sheet.paste(im,((n%8)*200,(n//8)*225+25));d.text(((n%8)*200+3,(n//8)*225+3),f"{s['name']} {s['t']} {'idle' if s.get('idle') else ''}",fill='white')
sheet.save(root/'all-square-contacts.jpg')
for cid in dict.fromkeys(s['id'] for s in rows):
 ss=[s for s in rows if s['id']==cid];sheet=Image.new('RGB',(1000,math.ceil(len(ss)/4)*285),'#252525');d=ImageDraw.Draw(sheet)
 for n,s in enumerate(ss):
  im=Image.open(root/s['file']).convert('RGB');x=max(100,min(im.width-140,s['x']));y=max(75,min(im.height-185,s['y']));im=im.crop((x-100,y-75,x+150,y+185));sheet.paste(im,((n%4)*250,(n//4)*285+25));d.text(((n%4)*250+3,(n//4)*285+3),f"{s['name']} {s['t']} {'idle' if s.get('idle') else ''}",fill='white')
 sheet.save(root/f'contacts-{cid}.jpg')
print(root/'all-square-contacts.jpg')
