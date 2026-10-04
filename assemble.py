"""Deterministically prepare facial cels and a transparent taskbar pet from approved art."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'references' / 'approved-concept.png'
GEN = ROOT / 'generated'
ASSETS = ROOT / 'assets'
QA = ROOT / 'qa'
ASSETS.mkdir(exist_ok=True)
QA.mkdir(exist_ok=True)
display_states = ['idle', 'blink', 'surprise', 'embarrassed', 'thinking', 'joy', 'annoyed', 'talking', 'teasing']
mouth_sources = {'mouth_closed':'talk_closed', 'mouth_teeth':'talk_teeth',
                 'mouth_open':'talking', 'mouth_wide':'joy', 'mouth_round':'surprise'}
pause_eyes = {'talk_pause_blink_half':'blink_half','talk_pause_blink':'blink'}
states = display_states + ['blink_half'] + list(mouth_sources) + list(pause_eyes)
base = Image.open(SOURCE).convert('RGB')
W, H = base.size
assert (W, H) == (1536, 1024)
arr = np.asarray(base).astype(np.int16)
base_pixels = np.asarray(base)

# The reference uses a slowly varying blue desktop and a dark taskbar. Estimate
# the backdrop from outer strips on every scanline so the hand stays intact.
ys = np.arange(H)
left = np.median(arr[:, 8:340], axis=1)
right = np.median(arr[:, 1370:1528], axis=1)
t = np.arange(W, dtype=np.float32)[None, :, None] / (W-1)
bg = left[:, None, :] * (1-t) + right[:, None, :] * t
dist = np.max(np.abs(arr-bg), axis=2)
rough = np.uint8(dist > 26) * 255
# Keep the only connected foreground component in the character region. The
# threshold is far above the gradient's normal noise but below fine hair edges.
rough[:, :520] = 0
rough[:100, :] = 0
rough = Image.fromarray(rough, 'L').filter(ImageFilter.MedianFilter(3))
# A tiny blur restores edge antialiasing; the pixel values in the generated
# drawing itself are left untouched.
mask = rough.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.65))
# The painted edge is antialiased against blue. Recover edge opacity from its
# distance to that blue backdrop, then unmatte its RGB to avoid a cyan fringe
# against a dark desktop.
alpha_f = np.minimum(np.asarray(mask,dtype=np.float32)/255,
                     np.clip((dist-7)/70,0,1))
# Matting applies only at the OUTER silhouette. Dark irises can be close in
# colour to the blue backdrop, but they are completely opaque inside the face.
interior = np.asarray(rough.filter(ImageFilter.MinFilter(5))) > 128
alpha_f[interior] = 1
alpha_f[365:540,855:1050] = 1
alpha_f[alpha_f < .08] = 0
alpha = np.uint8(np.round(alpha_f*255))
# Suppress one-pixel backdrop islands outside the main silhouette.
alpha[:, :520] = 0
box = Image.fromarray(alpha).getbbox()
print('mask bbox',box,'opaque pixels',int((alpha>128).sum()))
assert box is not None and box[0] > 500 and box[2] < 1400 and box[1] > 100 and box[3] < 1010
L,T,R,B = box
pad = 4
L,T,R,B = max(0,L-pad),max(0,T-pad),min(W,R+pad),min(H,B+pad)
cut_alpha = Image.fromarray(alpha[T:B,L:R], 'L')
cut_bg = np.uint8(np.clip(bg[T:B,L:R],0,255))

# This facial mask never reaches the outer silhouette or the hand. It lets each
# expression change while the body and taskbar contact remain pixel-identical.
fm = Image.new('L', (W,H))
fd = ImageDraw.Draw(fm)
fd.ellipse((826,331,1074,563), fill=255)
fm = fm.filter(ImageFilter.GaussianBlur(7))
face = np.asarray(fm, dtype=np.float32)[:,:,None]/255
mm = Image.new('L',(W,H))
ImageDraw.Draw(mm).ellipse((925,464,1022,529),fill=255)
mm = mm.filter(ImageFilter.GaussianBlur(4))
mouth = np.asarray(mm,dtype=np.float32)[:,:,None]/255

cards=[]
mouth_cards=[]
for state in states:
    source = mouth_sources.get(state,pause_eyes.get(state,state))
    edit = base if state == 'idle' else Image.open(GEN/f'{source}.png').convert('RGB')
    assert edit.size == base.size, state
    active_mask = mouth if state in mouth_sources else face
    mixed = base_pixels.copy()
    region = active_mask[:,:,0] > 0
    if state != 'idle':
        blended = np.uint8(np.clip(np.rint(base_pixels*(1-active_mask)+
                                           np.asarray(edit)*active_mask),0,255))
        mixed[region] = blended[region]
    if state in pause_eyes:
        closed = np.asarray(Image.open(GEN/'talk_closed.png').convert('RGB'))
        blended = np.uint8(np.clip(np.rint(mixed*(1-mouth)+closed*mouth),0,255))
        mixed[mouth[:,:,0]>0] = blended[mouth[:,:,0]>0]
    pixels = mixed[T:B,L:R].astype(np.float32)
    a = np.asarray(cut_alpha,dtype=np.float32)[:,:,None]/255
    pixels = np.uint8(np.clip((pixels-(1-a)*cut_bg)/np.maximum(a,.08),0,255))
    rgba = Image.fromarray(pixels, 'RGB').convert('RGBA')
    rgba.putalpha(cut_alpha)
    rgba.save(ASSETS/f'{state}.png', optimize=True)
    # Original-size face cells for visual identity review.
    crop=Image.fromarray(mixed[300:565,800:1090], 'RGB').resize((290,265))
    if state in display_states:cards.append(crop)
    if state in mouth_sources:mouth_cards.append((state,crop))

sheet = Image.new('RGB',(290*3, 300*3),'#263346')
d = ImageDraw.Draw(sheet)
for i,(state,card) in enumerate(zip(display_states,cards)):
    x=(i%3)*290; y=(i//3)*300
    sheet.paste(card,(x,y))
    d.text((x+8,y+271),state,fill='white')
sheet.save(QA/'expression-contact.png')

mouth_sheet=Image.new('RGB',(290*5,300),'#263346')
md=ImageDraw.Draw(mouth_sheet)
for i,(state,card) in enumerate(mouth_cards):
    mouth_sheet.paste(card,(i*290,0))
    md.text((i*290+8,271),state,fill='white')
mouth_sheet.save(QA/'mouth-contact.png')

preview = Image.new('RGBA',(R-L,B-T),'#89949f')
tile=Image.new('RGB',(32,32),'#d9dde1'); td=ImageDraw.Draw(tile)
td.rectangle((0,0,15,15),fill='#ecedef');td.rectangle((16,16,31,31),fill='#ecedef')
for yy in range(0,preview.height,32):
    for xx in range(0,preview.width,32):preview.paste(tile,(xx,yy))
preview.alpha_composite(Image.open(ASSETS/'idle.png'))
preview.save(QA/'transparent-preview.png')

icon = Image.open(ASSETS/'idle.png').crop((265,175,515,425))
icon.thumbnail((256,256),Image.Resampling.LANCZOS)
icon.save(ASSETS/'kurisu.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])

meta={'size':[R-L,B-T], 'anchor_y':913-T, 'anchor_x':650-L,
      'base_fps':24,'states':states,
      'illustrated_keyframes':12,'source_size':[W,H],
      'mask_bbox':[L,T,R,B]}
(ASSETS/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(meta,ensure_ascii=False))
