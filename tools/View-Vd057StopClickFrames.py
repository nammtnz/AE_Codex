from PIL import Image,ImageDraw
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'.ae-codex/inspection/vd057-stop-click-sequence'
labels=['before','CLICK','release','train moves']
print(len(list(p.glob('cue*.png'))))
for page in range(3):
 s=Image.new('RGB',(1080,1500));d=ImageDraw.Draw(s)
 for row,cue in enumerate(range(page*3,min(page*3+3,7))):
  for j in range(4):
   s.paste(Image.open(p/f'cue{cue}-{j}.png').convert('RGB').resize((270,480)),(j*270,row*500));d.text((j*270,row*500+480),f'{cue} {labels[j]}',fill='white')
 s.crop((0,0,1080,min(3,7-page*3)*500)).save(p/f'sheet{page}.png')
