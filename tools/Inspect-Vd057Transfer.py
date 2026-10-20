import subprocess,json
from pathlib import Path
from PIL import Image,ImageDraw
root=Path(__file__).resolve().parents[1]
out=root/'.ae-codex/inspection/vd057-raw';out.mkdir(exist_ok=True)
ff=r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
for tag,file,start,dur in [('a','Movie_015.mp4',15,16),('b','Movie_025.mp4',54,55)]:
 raw=subprocess.run([ff,'-v','error','-ss',str(start),'-i','E:/Task/Snacky Dash/RWD_VD007/FT/'+file,'-t',str(dur),'-vf','fps=2,scale=180:320','-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
 frames=[Image.frombytes('RGB',(180,320),raw[i:i+172800]) for i in range(0,len(raw)-172799,172800)]
 for page in range((len(frames)+29)//30):
  sheet=Image.new('RGB',(1800,1035));d=ImageDraw.Draw(sheet)
  for k,im in enumerate(frames[page*30:(page+1)*30]):
   n=page*30+k;t=start+n/2;sheet.paste(im,(k%10*180,k//10*345));d.text((k%10*180,k//10*345+320),f'raw {t:.1f}',fill='white')
  sheet.save(out/f'{tag}{page}.png')
print('done')
