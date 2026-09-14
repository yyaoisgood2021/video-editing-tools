"""Find candidate empty-health intervals from the 2 fps HUD cache."""

if __package__:
    from .common import configure
else:
    from common import configure


def main(argv=None):
    args = configure(__doc__, argv, video=False)
    R = ROOT = args.output_dir
    import numpy as np, json
    from PIL import Image, ImageDraw
    from pathlib import Path
    a = np.load(R / 'roi.npy')

    def norm(v):
        v = v.astype(float)
        v -= v.mean(axis=(-2, -1), keepdims=True)
        return v / np.maximum(np.sqrt((v * v).sum(axis=(-2, -1), keepdims=True)), 1e-08)
    gray = a.min(axis=3)
    top = norm(gray[:, 17:32, 24:94])
    bot = norm(gray[:, 65:80, 24:94])
    template = top[0]
    ct = (top * template).sum(axis=(1, 2))
    cb = (bot * template).sum(axis=(1, 2))
    row = (cb > ct).astype(int)
    bar = np.stack([a[:, 33:39, 30:93], a[:, 81:87, 30:93]], axis=1).astype(float)
    b = bar[np.arange(len(a)), row]
    red, green, blue = (b[:, :, :, 0], b[:, :, :, 1], b[:, :, :, 2])
    filled = (green - blue > 28) & (green > red - 18) & (green > 75) | (red - green > 38) & (red - blue > 30) & (red > 100)
    count = (filled.sum(axis=1) >= 2).sum(axis=1)
    visible = np.maximum(ct, cb) > 0.48
    empty = (count < 4) & visible

    def runs(mask):
        edges = np.diff(np.r_[False, mask, False].astype(int))
        return list(zip(np.where(edges == 1)[0], np.where(edges == -1)[0]))
    r = runs(empty)
    print('row switches:', [(s / 2, e / 2) for s, e in runs(row == 1)])
    print('empty:', [(s / 2, e / 2, round(float(np.max(np.maximum(ct, cb)[s:e])), 2)) for s, e in r])
    np.savez(R / 'metrics.npz', row=row, count=count, visible=visible, ct=ct, cb=cb)
    (R / 'candidate.json').write_text(json.dumps([(int(s), int(e)) for s, e in r]))
    indices = sorted(set((i for s, e in r for i in [max(0, s - 2), s, (s + e) // 2, min(len(a) - 1, e)])))
    for page, start in enumerate(range(0, len(indices), 48)):
        ids = indices[start:start + 48]
        sheet = Image.new('RGB', (840, 135 * ((len(ids) + 5) // 6)), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        for j, i in enumerate(ids):
            x = j % 6 * 140
            y = j // 6 * 135
            sheet.paste(Image.fromarray(a[i]), (x, y + 25))
            d.text((x + 2, y + 4), f'{i / 2 // 60:02.0f}:{i / 2 % 60:04.1f} C{count[i]}', fill='white')
        sheet.save(R / f'candidate_{page}.jpg')


if __name__ == "__main__":
    main()
