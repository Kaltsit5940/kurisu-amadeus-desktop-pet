"""Render the exact cel timing used by the pet for visual QA."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from pet import TALK_DURATION, speech_cel

ROOT=Path(__file__).resolve().parent
assets=ROOT/'assets'
qa=ROOT/'qa'
images={p.stem:Image.open(p).convert('RGBA') for p in assets.glob('*.png')}
font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
fps=24


def make_card(name,title):
    im=images[name].crop((223,147,533,432)).resize((310,285),Image.Resampling.LANCZOS)
    card=Image.new('RGB',(310,320),'#263346')
    card.paste(im,(0,0),im)
    ImageDraw.Draw(card).text((12,292),title,font=font,fill='white')
    return card


cases=[('惊讶','surprise',1.85),('思考','thinking',2.65),('说话','talking',TALK_DURATION)]
frames=[]
for title,state,duration in cases:
    for i in range(round(.3*fps)):
        frames.append(make_card('idle',title))
    for i in range(round(duration*fps)):
        t=i/fps
        if state=='thinking' and t<.18:
            cel='blink_half' if t<.055 or t>=.13 else 'blink'
        elif state=='talking':
            cel=speech_cel(t)
        else:cel=state
        frames.append(make_card(cel,title))
    for i in range(round(.35*fps)):
        frames.append(make_card('idle',title))

paletted=[f.quantize(colors=128,method=Image.Quantize.FASTOCTREE) for f in frames]
paletted[0].save(qa/'expression-preview.gif',save_all=True,append_images=paletted[1:],
                 optimize=True,duration=round(1000/fps),loop=0,disposal=2)
print(len(frames),'frames, no blended faces',qa/'expression-preview.gif')
