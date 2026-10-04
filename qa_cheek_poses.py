"""Review the raw illustrated key poses before turning them into pet sprites."""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
paths=[ROOT/'references'/'approved-concept.png',
       *[ROOT/'generated'/f'cheek_raise_{v}.png' for v in (20,35,50,65,80,90)],
       ROOT/'generated'/'cheek_raise_100.png']
labels=['idle','20%','35%','50%','65%','80%','90%','hold']
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
out=Image.new('RGB',(430*4,420*2),'#263346')
d=ImageDraw.Draw(out)
base=np.asarray(Image.open(paths[0]).convert('RGB'),dtype=np.int16)
for i,(path,label) in enumerate(zip(paths,labels)):
    im=Image.open(path).convert('RGB')
    assert im.size==(1536,1024),path
    thumb=im.crop((520,130,1410,985)).resize((400,385),Image.Resampling.LANCZOS)
    x=(i%4)*430;y=(i//4)*420
    out.paste(thumb,(x+15,y+5))
    d.text((x+15,y+391),label,font=font,fill='white')
    a=np.asarray(im,dtype=np.int16)
    face=np.abs(a[335:545,835:1045]-base[335:545,835:1045])
    outside=np.abs(a[150:900,520:820]-base[150:900,520:820])
    print(label,'face mean',round(float(face.mean()),2),'left/body mean',round(float(outside.mean()),2))
out.save(ROOT/'qa'/'cheek-pose-storyboard.png')
