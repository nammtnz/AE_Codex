from pathlib import Path
from array import array
import json, math, subprocess
from PIL import Image
root = Path(__file__).resolve().parents[1]
folder = root/'assets/rwd007-praise'
sheet = Image.open(folder/'perfect-cool-sheet.png').convert('RGBA')
if sheet.getchannel('A').getextrema()[0] == 255:
    raise RuntimeError('Missing transparency')
for index, name in enumerate(['perfect', 'cool']):
    cell = sheet.crop((0, index*sheet.height//2, sheet.width, (index+1)*sheet.height//2))
    bounds = cell.getchannel('A').point(lambda a: 255 if a>16 else 0).getbbox()
    if not bounds: raise RuntimeError('Empty word')
    word = cell.crop(bounds)
    png = Image.new('RGBA', (word.width+24, word.height+24))
    png.paste(word, (12,12))
    png.save(folder/f'{name}-3d-trim.png')
ffmpeg = r'C:/Users/nguye/AppData/Local/XGetter/externals/ffmpeg.exe'
choices = [
    ('pop', 'E:/Audio/SFX/Cartoon/Button/cartoon-pop.mp3', -15),
    ('cool', 'E:/Audio/SFX/Cartoon/8 Epic Garden_SFX/Process Success.wav', -12),
    ('perfect', 'E:/Audio/SFX/Cartoon/8 Epic Garden_SFX/retro-positive-game-bling-pack/Positive - Bling 4.wav', -10),
]
reports = []
for kind, path, target in choices:
    raw = subprocess.run([ffmpeg,'-v','error','-i',path,'-vn','-ac','2','-ar','48000','-f','f32le','pipe:1'],capture_output=True,check=True).stdout
    values = array('f'); values.frombytes(raw)
    active = [i for i in range(0,len(values),2) if max(abs(values[i]),abs(values[i+1])) > 10**(-42/20)]
    start = max(0,active[0]//2/48000-.005)
    end = min(len(values)/96000,active[-1]//2/48000+.075)
    cut = values[round(start*48000)*2:round(end*48000)*2]
    peak = 20*math.log10(max(abs(v) for v in cut))
    reports.append(dict(kind=kind,file=path,offset=start,duration=end-start,totalDuration=len(values)/96000,peak_dbfs=peak,gain=target-peak))
(root/'.ae-codex/rwd007-praise-sfx-analysis.json').write_text(json.dumps(reports,indent=2),encoding='utf-8')
print(json.dumps(reports,indent=2))
