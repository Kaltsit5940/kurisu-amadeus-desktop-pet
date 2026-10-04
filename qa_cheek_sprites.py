"""Preview the actual transparent cheek action against a neutral desktop."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pet import CHEEK_SEQUENCE

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
QA = ROOT / 'qa'
QA.mkdir(exist_ok=True)
names = ['idle','cheek_20','cheek_35','cheek_50','cheek_65',
         'cheek_80','cheek_90','cheek_100','cheek_tap']
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
size = (408, 421)
sheet = Image.new('RGB',(size[0]*3,(size[1]+30)*3),'#2e3846')
draw = ImageDraw.Draw(sheet)
for i,name in enumerate(names):
    sprite = Image.open(ASSETS / f'{name}.png').convert('RGBA')
    card = Image.new('RGB',sprite.size,'#737d89')
    card.paste(sprite,(0,0),sprite)
    card.thumbnail(size, Image.Resampling.LANCZOS)
    x=(i%3)*size[0]; y=(i//3)*(size[1]+30)
    sheet.paste(card,(x,y))
    draw.text((x+8,y+size[1]+3),name,font=font,fill='white')
sheet.save(QA / 'cheek-transparent-storyboard.png')

frames=[]
for name,duration in CHEEK_SEQUENCE:
    sprite=Image.open(ASSETS/f'{name}.png').convert('RGBA')
    bg=Image.new('RGB',sprite.size,'#737d89')
    bg.paste(sprite,(0,0),sprite)
    bg.thumbnail((480,480),Image.Resampling.LANCZOS)
    for _ in range(round(duration*24)):
        frames.append(bg)
frames[0].save(QA/'cheek-preview.gif',save_all=True,append_images=frames[1:],
               duration=round(1000/24),loop=0,optimize=True)
print('frames',len(frames),'total seconds',len(frames)/24)
