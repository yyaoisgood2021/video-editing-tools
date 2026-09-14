"""Create contact sheets for the recording-specific review windows."""

if __package__:
    from .common import configure
else:
    from common import configure


def main(argv=None):
    args = configure(__doc__, argv, video=False)
    R = ROOT = args.output_dir
    import numpy as np
    from PIL import Image, ImageDraw
    from pathlib import Path
    a = np.load(R / 'roi.npy')
    ranges = [(0, 45), (184, 207), (270, 284), (307, 321), (466, 480), (768, 780), (903, 921), (1174, 1184), (1262, 1276), (1447, 1458), (1848, 1866), (1905, 1927), (2012, 2030), (2037, 2049)]
    for k, (s, e) in enumerate(ranges):
        ids = range(s * 2, min(e * 2, len(a)), 2)
        if not ids:
            continue
        w = 168
        h = 153
        sheet = Image.new('RGB', (w * 8, h * ((len(ids) + 7) // 8)), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        for j, i in enumerate(ids):
            x = j % 8 * w
            y = j // 8 * h
            sheet.paste(Image.fromarray(a[i]).resize((168, 127)), (x, y + 25))
            d.text((x + 5, y + 5), f'{i / 2 // 60:02.0f}:{i / 2 % 60:04.1f}', fill='white')
        sheet.save(R / f'review_{k}.jpg')


if __name__ == "__main__":
    main()
