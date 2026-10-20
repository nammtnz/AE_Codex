from pathlib import Path
import subprocess, json
from PIL import Image, ImageDraw
root=Path(__file__).resolve().parents[1]
folder=root/'.ae-codex/rwd007-hand-analysis'
folder.mkdir(exist_ok=True)
ff=r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
jobs=[('first',r'E:/Task/Snacky Dash/RWD_VD007/FT/Movie_009.mp4',63.3666667,8.1,1,0,[(270,218),(51,360),(488,360),(270,633),(379,462),(488,462),(51,736),(488,736),(270,838)]),('second',r'E:/Task/Snacky Dash/RWD_VD007/FT/Movie_012.mp4',75.9888889,16.1,.6,12.3666667,[(186,252),(354,252),(46,257),(493,270),(186,388),(354,388),(186,533),(354,533),(186,742),(354,742),(186,782)])]
events=[]
for name,path,start,dur,ratio,outstart,points in jobs:
 points=[(round((x-270)/1.2133333333+270),round((y-480)/1.2133333333+480)) for x,y in points]
 raw=subprocess.run([ff,'-v','error','-ss',str(start),'-i',path,'-t',str(dur),'-vf','fps=20,scale=540:960','-an','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True).stdout
 size=540*960*3
 images=[Image.frombytes('RGB',(540,960),raw[i:i+size]) for i in range(0,len(raw)-size+1,size)]
 entries=[]
 for fi,im in enumerate(images):
  counts=[]
  for x,y in points:
   region=im.crop((x-14,y-14,x+15,y+15))
   purple=sum(1 for r,g,b in region.getdata() if 45<r<195 and 35<g<190 and b>r+15 and b>g+15)
   orange=sum(1 for r,g,b in region.getdata() if r>170 and 115<g<205 and b<140 and r>g+15)
   counts.append([purple,orange])
  entries.append([outstart+fi/20*ratio,counts])
 (folder/f'{name}-counts.json').write_text(json.dumps(dict(points=points,samples=entries)),encoding='utf-8')
 images[0].save(folder/f'{name}-first.png')
 for pi,pt in enumerate(points):
  runs=[];at=None
  for t,counts in entries:
   if counts[pi][0]>18 and at is None: at=t
   if counts[pi][0]<=18 and at is not None: runs.append([round(at,3),round(t,3)]);at=None
  if at is not None:runs.append([round(at,3),round(entries[-1][0],3)])
  print('TILE',name,pi+1,pt,runs)
 # Source frames every .5s of output, with point IDs for route review.
 picks=list(range(0,len(images),round(.5/ratio*20)))
 for part in range(0,len(picks),20):
  canvas=Image.new('RGB',(5*216,4*404),(35,35,35));d=ImageDraw.Draw(canvas)
  for ni,fi in enumerate(picks[part:part+20]):
   im=images[fi].copy();dr=ImageDraw.Draw(im)
   for pi,(x,y) in enumerate(points):dr.text((x+16,y-13),str(pi+1),fill='red')
   im=im.resize((216,384));x=ni%5*216;y=ni//5*404
   canvas.paste(im,(x,y+20));d.text((x+3,y+3),f'{name} t={outstart+fi/20*ratio:.2f}',fill='white')
  canvas.save(folder/f'{name}-sheet-{part//20}.jpg')
 print(name,'samples',len(images),'sheets',(len(picks)+19)//20)
hand=Image.open(r'E:/Icon/Tay/ChatGPT Image 17_19_01 10 thg 9, 2026.png')
print('HAND',hand.size,hand.mode,'alpha',hand.getchannel('A').getextrema() if hand.mode=='RGBA' else None)
