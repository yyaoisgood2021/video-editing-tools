"""Create two 3 by 4 collages at the verified recording timestamps."""

if __package__:
    from .common import configure
else:
    from common import configure


def main(argv=None):
    args = configure(__doc__, argv, video=True)
    R = ROOT = args.output_dir
    FF = args.ffmpeg
    SRC = str(args.source)
    from pathlib import Path
    import subprocess
    OUT = R / 'collage_frames'
    OUT.mkdir(exist_ok=True)
    times = [190.75, 315.75, 474.75, 774.5, 914, 1269, 1454.5, 1498, 1856, 1918, 2023.5, 2044]
    font = "font='Arial'"

    def run(args):
        subprocess.run([str(FF), '-hide_banner', '-loglevel', 'error', '-y', *args], check=True)
    for n, t in enumerate(times, 1):
        label = f'{n:02d}   {int(t // 60):02d}\\:{t % 60:05.2f}'
        raw = OUT / f'frame_{n:02d}.png'
        run(['-ss', str(t), '-i', SRC, '-frames:v', '1', str(raw)])
        filt = f"[0:v]split=2[full][hud];[full]crop=1030:710:125:4,pad=1030:756:0:46:color=0x171b23,drawtext={font}:text='{label}':fontsize=29:fontcolor=white:x=18:y=8[base];[hud]crop=140:106:1000:74,scale=350:265:flags=neighbor,pad=358:273:4:4:color=0xffcc66[zoom];[base][zoom]overlay=654:465[out]"
        run(['-i', str(raw), '-filter_complex', filt, '-map', '[out]', '-frames:v', '1', str(OUT / f'cell_{n:02d}.png')])
        filt = f"crop=140:106:1000:74,scale=420:318:flags=neighbor,pad=420:364:0:46:color=0x171b23,drawtext={font}:text='{label}':fontsize=26:fontcolor=white:x=16:y=9"
        run(['-i', str(raw), '-vf', filt, '-frames:v', '1', str(OUT / f'hud_{n:02d}.png')])
    for prefix, name in [('cell', 'yaoyao_12次空血条_3列4行.png'), ('hud', 'yaoyao_空血条特写_3列4行.png')]:
        run(['-framerate', '1', '-start_number', '1', '-i', str(OUT / f'{prefix}_%02d.png'), '-vf', 'tile=3x4:nb_frames=12:padding=12:margin=12:color=0x0c1016', '-frames:v', '1', str(R / name)])
    print('Created both collages.')


if __name__ == "__main__":
    main()
