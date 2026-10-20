from pathlib import Path
import subprocess, json
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parents[1]
ff = r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
src = r'E:/Task/Snacky Dash/RWD_VD007/FT/Movie_012.mp4'
groups = [(18.94, 19.28, (215, 80, 270, 165)), (20.90, 21.12, (70, 185, 120, 245)), (21.28, 21.58, (65, 110, 125, 170))]
sheets = []
for gi, (start, end, box) in enumerate(groups):
    times = [round(start+i*.02, 3) for i in range(round((end-start)/.02)+1)]
    sheet = Image.new('RGB', (6*180, ((len(times)+5)//6)*205), '#303030')
    d = ImageDraw.Draw(sheet)
    for i,t in enumerate(times):
        st = 75.9888889+(t-12.3666667)/.6
        raw = subprocess.run([ff,'-v','error','-ss',str(st),'-i',src,'-frames:v','1','-vf','scale=270:480','-f','rawvideo','-pix_fmt','rgb24','pipe:1'], capture_output=True,check=True).stdout
        im = Image.frombytes('RGB',(270,480),raw[:270*480*3]).crop(box)
        im.thumbnail((174,174))
        x=(i%6)*180;y=(i//6)*205
        sheet.paste(im,(x+(180-im.width)//2,y+25))
        d.text((x+5,y+5),f'{t:.2f}s',fill='white')
    out=root/f'.ae-codex/rwd007-late-departure-{gi}.png'
    sheet.save(out)
    sheets.append(str(out))
print(json.dumps(sheets))
