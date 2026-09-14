from argparse import Namespace
import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from ass_to_video import find_ffmpeg, inspect_ass, make_command, render, run_capture, seconds


FIXTURE = r"""[Script Info]
ScriptType: v4.00+
PlayResX: 320
PlayResY: 180
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,24,&H00FFFFFF,&H00FFFFFF,&H00000000,&HFF000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:02.00,Default,,0,0,0,,{\an7\move(0,50,200,50)\p1\1c&H406080&\1a&H80&}m 0 0 l 30 0 30 30 0 30
"""


class AssVideoTests(unittest.TestCase):
    def test_timestamp_validation(self):
        self.assertEqual(seconds("01:02:03.25"), 3723.25)
        for value in ("nan", "inf", "-1", "00:99"):
            with self.assertRaises(ValueError):
                seconds(value)

    def test_render_crop_alpha_color_and_motion(self):
        try:
            ffmpeg = find_ffmpeg()
        except ValueError:
            self.skipTest("Install FFmpeg to run video integration test")
        with tempfile.TemporaryDirectory() as temporary:
            # Exercise paths which cannot safely be interpolated into a filter.
            work = Path(temporary) / "字幕 [test], it's safe"
            work.mkdir()
            source = work / "测试字幕.ass"
            source.write_text(FIXTURE, encoding="utf-8-sig")
            _, resolution, intervals = inspect_ass(source)
            self.assertEqual(resolution["playresx"], 320)
            self.assertEqual(intervals, [(0, 2)])
            output = work / "结果.mov"
            args = Namespace(input=source, output=output, start="1", end="2", fps="10",
                             width=None, height=None, quality=4, threads=2,
                             ffmpeg=str(ffmpeg), ffprobe=None, fonts_dir=None, force=False)
            with contextlib.redirect_stdout(io.StringIO()):
                report = render(args)
            self.assertEqual(report["frames"], 10)
            self.assertEqual(report["duration"], 1)
            self.assertEqual(report["place_at_seconds"], 1)
            self.assertEqual(report["alpha_min"], 0)
            self.assertTrue(120 <= report["alpha_max"] <= 135, report)
            centers = []
            for time in (0, 0.5):
                raw = run_capture([ffmpeg, "-v", "error", "-ss", str(time), "-i", output,
                                   "-frames:v", "1", "-pix_fmt", "rgba", "-f", "rawvideo", "pipe:1"])
                self.assertEqual(len(raw), 320 * 180 * 4)
                pixels = [i for i in range(320*180) if raw[i*4+3] > 100]
                centers.append(sum(i % 320 for i in pixels) / len(pixels))
                center = int(centers[-1])
                rgba = raw[(65*320+center)*4:(65*320+center)*4+4]
                # Straight alpha retains color intensity, even at 50% opacity.
                for actual, expected in zip(rgba, (128, 96, 64, 127)):
                    self.assertLessEqual(abs(actual-expected), 8, (list(rgba), expected))
            self.assertAlmostEqual(centers[0], 114.5, delta=2)
            self.assertAlmostEqual(centers[1]-centers[0], 50, delta=2)
            original = output.read_bytes()
            with self.assertRaisesRegex(ValueError, "Output exists"):
                render(args)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
