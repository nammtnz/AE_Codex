from pathlib import Path
from PIL import Image,ImageDraw
import json,sys
folder=Path(sys.argv[1]).resolve()
items=json.loads((folder/'click-review.json').read_text(encoding='utf-8-sig'))
for cid in [671,811,1059,1132]:
    width,height=(270,480) if cid in (671,1059) else (480,270)
    sheet=Image.new('RGB',(width*4,(height+24)*3),'#252530');draw=ImageDraw.Draw(sheet)
    for n,row in enumerate([r for r in items if r['id']==cid]):
        pic=Image.open(folder/row['file']).convert('RGB');pic.thumbnail((width,height))
        x=n%4*width;y=n//4*(height+24)
        sheet.paste(pic,(x,y+24));draw.text((x+5,y+5),f"click {row['event']} / {row['time']:.2f}s",fill='white')
    sheet.save(folder/f'review-c{cid}.jpg',quality=95)
print(folder)
