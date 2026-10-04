"""Append the single cheek-prop action to the approved transparent pet cels."""
from pathlib import Path
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
GEN = ROOT / 'generated'
META = ASSETS / 'manifest.json'
POSES = (20, 35, 50, 65, 80, 90, 100)


def matting(image):
    pixels = np.asarray(image.convert('RGB'), dtype=np.int16)
    h, w, _ = pixels.shape
    left = np.median(pixels[:, 8:340], axis=1)
    right = np.median(pixels[:, 1370:1528], axis=1)
    t = np.arange(w, dtype=np.float32)[None, :, None] / (w - 1)
    bg = left[:, None, :] * (1-t) + right[:, None, :] * t
    dist = np.max(np.abs(pixels - bg), axis=2)
    rough = np.uint8(dist > 26) * 255
    rough[:, :520] = 0
    rough[:100, :] = 0
    rough = Image.fromarray(rough, 'L').filter(ImageFilter.MedianFilter(3))
    mask = rough.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(.65))
    alpha = np.minimum(np.asarray(mask, dtype=np.float32)/255,
                       np.clip((dist-7)/70, 0, 1))
    interior = np.asarray(rough.filter(ImageFilter.MinFilter(5))) > 128
    alpha[interior] = 1
    alpha[365:540, 855:1050] = 1
    alpha[alpha < .08] = 0
    return pixels, bg, np.uint8(np.round(alpha*255))


def main():
    meta = json.loads(META.read_text(encoding='utf-8'))
    assert not any(s.startswith('cheek_') for s in meta['states']), 'Run assemble.py first'
    l, t, old_r, b = meta['mask_bbox']
    pose_data = {}
    for key in POSES:
        image = Image.open(GEN / f'cheek_raise_{key}.png').convert('RGB')
        assert image.size == tuple(meta['source_size'])
        pixels, bg, alpha = matting(image)
        box = Image.fromarray(alpha).getbbox()
        print('cheek', key, 'mask', box)
        assert box and box[0] >= l-8 and box[1] >= t-8 and box[3] <= b+8
        pose_data[key] = (pixels, bg, alpha)

    # The original arm stays untouched. Space is added to the right so the
    # emerging second hand is never clipped by the original silhouette crop.
    r = min(1536, max(old_r, *(Image.fromarray(data[2]).getbbox()[2] + 4
                               for data in pose_data.values())))
    assert r < 1430
    old_size = tuple(meta['size'])
    new_size = (r-l, b-t)
    for state in meta['states']:
        old = Image.open(ASSETS / f'{state}.png').convert('RGBA')
        assert old.size == old_size
        padded = Image.new('RGBA', new_size, (0, 0, 0, 0))
        padded.paste(old, (0, 0))
        padded.save(ASSETS / f'{state}.png', optimize=True)

    names = []
    for key in POSES:
        pixels, bg, alpha = pose_data[key]
        region = pixels[t:b, l:r].astype(np.float32)
        backdrop = bg[t:b, l:r].astype(np.float32)
        a = alpha[t:b, l:r].astype(np.float32)[:, :, None] / 255
        rgb = np.uint8(np.clip((region-(1-a)*backdrop)/np.maximum(a, .08), 0, 255))
        cel = Image.fromarray(rgb, 'RGB').convert('RGBA')
        cel.putalpha(Image.fromarray(alpha[t:b, l:r], 'L'))
        name = f'cheek_{key}'
        cel.save(ASSETS / f'{name}.png', optimize=True)
        names.append(name)

    # The extra hand makes one gentle tap while the cheek is supported.
    hold = Image.open(ASSETS / 'cheek_100.png').convert('RGBA')
    tap = Image.open(GEN / 'cheek_tap.png').convert('RGB')
    tap_rgb, tap_bg, tap_alpha = matting(tap)
    ta = tap_alpha[t:b, l:r].astype(np.float32)[:, :, None] / 255
    tap_rgb = np.uint8(np.clip((tap_rgb[t:b, l:r].astype(np.float32) -
                               (1-ta)*tap_bg[t:b, l:r]) / np.maximum(ta, .08), 0, 255))
    tap_cel = Image.fromarray(tap_rgb, 'RGB').convert('RGBA')
    tap_cel.putalpha(Image.fromarray(tap_alpha[t:b, l:r], 'L'))
    local_mask = Image.new('L', new_size)
    ImageDraw.Draw(local_mask).polygon(
        [(x-l, y-t) for x, y in ((585,891),(604,860),(624,847),(668,866),
                                 (707,891),(735,915),(730,954),(697,955),
                                 (680,991),(612,991),(602,946))], fill=255)
    local_mask = local_mask.filter(ImageFilter.GaussianBlur(3))
    hold.paste(tap_cel, (0, 0), local_mask)
    hold.save(ASSETS / 'cheek_tap.png', optimize=True)
    names.append('cheek_tap')

    meta['states'] += names
    meta['size'] = list(new_size)
    meta['mask_bbox'] = [l, t, r, b]
    meta['illustrated_keyframes'] += len(POSES) + 1
    meta['cheek_action'] = names
    META.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'sprite_size': new_size, 'cheek_cels': names}, ensure_ascii=False))


if __name__ == '__main__':
    main()
