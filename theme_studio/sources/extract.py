"""Image -> dominant colours, with Pillow. Deterministic: same images, same result."""
import math

from PIL import Image

from ..core.color import rgb_to_hex, to_oklch


def _oklab(hexcol):
    L, C, H = to_oklch(hexcol)
    return L, C * math.cos(math.radians(H)), C * math.sin(math.radians(H))


def dominant(path, n=16):
    """[(hex, share)] for one image, share summing to 1."""
    img = Image.open(path).convert("RGB")
    img.thumbnail((256, 256))
    q = img.quantize(colors=n, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    total = img.width * img.height
    out = []
    for count, idx in sorted(q.getcolors(), reverse=True):
        rgb = pal[idx * 3: idx * 3 + 3]
        out.append((rgb_to_hex(rgb), count / total))
    return out + vivid_details(img, total)


def vivid_details(img, total, bins=18):
    """Second pass over only the strongly coloured pixels, grouped by hue.

    The main pass is ruled by area, so a gold trim or yellow fists covering 2% of the
    picture get folded into a big neighbour. Accents are often exactly those details.
    Grouping by hue (20° slices) gives every colour family its own average, however
    few pixels it has.
    """
    hsv = img.convert("HSV")
    groups = {}
    for (r, g, b), (h, sat, val) in zip(img.getdata(), hsv.getdata()):
        if sat > 100 and val > 70:
            acc = groups.setdefault(h * bins // 256, [0, 0, 0, 0])
            acc[0] += r; acc[1] += g; acc[2] += b; acc[3] += 1
    out = []
    for r, g, b, n in groups.values():
        if n / total > 0.002:
            out.append((rgb_to_hex((r / n, g / n, b / n)), n / total))
    return sorted(out, key=lambda x: -x[1])


def extract(paths, n=16):
    """Combine several images. The first one (main monitor) counts most."""
    pool = {}
    for i, path in enumerate(paths):
        weight = 1.0 if i == 0 else 0.5
        for hexcol, share in dominant(path, n):
            pool[hexcol] = pool.get(hexcol, 0) + share * weight
    # Merge colours that look the same
    merged = []
    for hexcol, w in sorted(pool.items(), key=lambda kv: -kv[1]):
        lab = _oklab(hexcol)
        for item in merged:
            if math.dist(lab, item[2]) < 0.03:
                item[1] += w
                break
        else:
            merged.append([hexcol, w, lab])
    total = sum(w for _, w, _ in merged) or 1
    return [(h, w / total) for h, w, _ in sorted(merged, key=lambda m: -m[1])]
