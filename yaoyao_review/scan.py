"""Extract the fixed health HUD at 2 fps and create overview sheets."""

if __package__:
    from .common import configure
else:
    from common import configure


def main(argv=None):
    args = configure(__doc__, argv, video=True)
    R = ROOT = args.output_dir
    FF = args.ffmpeg
    SRC = str(args.source)
    import subprocess, pathlib, numpy as np
    from PIL import Image, ImageDraw
    cmd = [str(FF), '-hide_banner', '-loglevel', 'error', '-i', SRC, '-vf', 'fps=2,crop=140:106:1000:74', '-an', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-']
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    frames = []
    while True:
        data = p.stdout.read(140 * 106 * 3)
        if len(data) != 140 * 106 * 3:
            break
        frames.append(np.frombuffer(data, np.uint8).reshape(106, 140, 3).copy())
        if len(frames) % 600 == 0:
            print(f'Scanned {len(frames) / 2:.0f} seconds', flush=True)
    p.stdout.close()
    if p.wait():
        raise RuntimeError('FFmpeg could not decode the source video')
    if not frames:
        raise ValueError('No frames extracted; verify the source video and crop coordinates')
    a = np.stack(frames)
    np.save(ROOT / 'roi.npy', a)
    for page, start in enumerate(range(0, len(a), 1200)):
        indices = list(range(start, min(start + 1200, len(a)), 40))
        sheet = Image.new('RGB', (700, 138 * ((len(indices) + 4) // 5)), (24, 24, 24))
        d = ImageDraw.Draw(sheet)
        for j, i in enumerate(indices):
            x = j % 5 * 140
            y = j // 5 * 138
            sheet.paste(Image.fromarray(a[i]), (x, y + 25))
            d.text((x + 5, y + 5), f'{i / 2 // 60:02.0f}:{i / 2 % 60:04.1f}', fill='white')
        sheet.save(ROOT / f'overview_{page}.jpg')
    print(f'Done {len(a)} frames', flush=True)


if __name__ == "__main__":
    main()
