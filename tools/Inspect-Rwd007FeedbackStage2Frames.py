from pathlib import Path
import io, json, math, subprocess
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
FF=r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
MOVIE=r'E:/Task/Snacky Dash/RWD_VD007/FT/Movie_012.mp4'
START=-33.2266666666667
OUT=ROOT/'.ae-codex/inspection/rwd007-feedback-stage2'
OUT.mkdir(parents=True,exist_ok=True)
segments=[('collect-early',13.0,15.4,1/15),('tray-first',15.4,15.9,1/30),('tray-second',16.7,17.2,1/30),('tray-third',17.9,18.5,1/30),('final-collect',20.0,21.55,1/15),('tray-final',21.55,22.1,1/30)]
reports=[]
for label,a,b,dt in segments:
    times=[round(a+i*dt,6) for i in range(round((b-a)/dt)+1)]
    cols,cw,ch=6,324,318
    sheet=Image.new('RGB',(cols*cw,math.ceil(len(times)/cols)*ch),'#222222')
    draw=ImageDraw.Draw(sheet)
    for i,t in enumerate(times):
        source=(t-START)/.6
        data=subprocess.run([FF,'-v','error','-ss',str(source),'-i',MOVIE,'-frames:v','1','-vf','crop=1080:960:0:300,scale=324:288','-f','image2pipe','-vcodec','png','pipe:1'],capture_output=True,check=True).stdout
        im=Image.open(io.BytesIO(data)).convert('RGB')
        x,y=(i%cols)*cw,(i//cols)*ch
        sheet.paste(im,(x,y+30));draw.text((x+6,y+7),f'root{t:.4f} | src{source:.4f}',fill='white')
    path=OUT/(label+'.jpg');sheet.save(path,quality=95)
    reports.append(str(path))
print(json.dumps(reports,indent=2))
