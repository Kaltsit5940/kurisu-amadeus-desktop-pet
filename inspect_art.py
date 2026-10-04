from pathlib import Path
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent
for path in [ROOT/'references/approved-concept.png', *sorted((ROOT/'generated').glob('*.png'))]:
    a = np.array(Image.open(path).convert('RGB'), dtype=np.int16)
    if path.name == 'approved-concept.png':
        base = a
        for y in [100, 500, 800, 910, 912, 913, 915, 960, 1000]:
            print('BACKGROUND',y,[(x,a[y,x].tolist()) for x in [20,200,400,500,1400,1515]])
    else:
        r = np.abs(a-base)
        outside = r.copy(); outside[330:555,805:1080] = 0
        print(path.name, 'face',float(r[330:555,805:1080].mean()),'outside',float(outside.mean()), 'outside >20',float((outside>20).mean()))
