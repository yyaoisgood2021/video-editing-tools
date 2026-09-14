"""Extract fixed candidate windows at 24 fps for manual verification."""

if __package__:
    from .common import configure
else:
    from common import configure


def main(argv=None):
    args = configure(__doc__, argv, video=True)
    R = ROOT = args.output_dir
    FF = args.ffmpeg
    SRC = str(args.source)
    import subprocess, numpy as np
    from PIL import Image, ImageDraw
    from pathlib import Path
    ranges = [(186, 194), (310, 318), (470, 478), (770, 777), (908, 918), (1265, 1273), (1450, 1458), (1493, 1502), (1853, 1861), (1911, 1922), (2016, 2025), (2038, 2047)]
    for k, (s, e) in enumerate(ranges):
        raw = subprocess.check_output([str(FF), '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(s), '-i', SRC, '-t', str(e - s), '-vf', 'fps=24,crop=140:106:1000:74', '-an', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'])
        a = np.frombuffer(raw, np.uint8).reshape(-1, 106, 140, 3)
        np.save(R / f'detail_{k}.npy', a)
        ids = range(0, len(a), 6)
        w = 168
        h = 153
        sheet = Image.new('RGB', (w * 8, h * ((len(ids) + 7) // 8)), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        for j, i in enumerate(ids):
            t = s + i / 24
            x = j % 8 * w
            y = j // 8 * h
            sheet.paste(Image.fromarray(a[i]).resize((168, 127)), (x, y + 25))
            d.text((x + 5, y + 5), f'{int(t // 60):02}:{t % 60:05.2f}', fill='white')
        sheet.save(R / f'detail_{k}.jpg')
        print(k, s, e, flush=True)
    for t in [189, 772, 910, 1455, 1497, 2044]:
        subprocess.run([str(FF), '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(t), '-i', SRC, '-frames:v', '1', str(R / f'full_{t}.png')], check=True)


if __name__ == "__main__":
    main()
