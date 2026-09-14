"""Visualize the detected health row over the entire cached timeline."""

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
    m = np.load(R / 'metrics.npz')
    row = m['row']
    for page in range((len(a) + 599) // 600):
        sheet = Image.new('RGB', (900, 780), (25, 25, 25))
        d = ImageDraw.Draw(sheet)
        for j in range(5):
            minute = page * 5 + j
            d.text((j * 180 + 40, 5), f'{minute:02}:00', fill='white')
            for sub in range(120):
                i = minute * 120 + sub
                if i >= len(a):
                    break
                y = 34 + int(row[i]) * 48
                patch = a[i, y:y + 4, 29:94]
                sheet.paste(Image.fromarray(patch).resize((130, 6)), (j * 180 + 40, 30 + sub * 6))
                if sub % 10 == 0:
                    d.text((j * 180 + 1, 30 + sub * 6), f'{sub / 2:02.0f}', fill='white')
        sheet.save(R / f'timeline_{page}.png')


if __name__ == "__main__":
    main()
