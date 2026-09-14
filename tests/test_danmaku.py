import random
import re
import tempfile
import unittest
from pathlib import Path

from danmaku_to_ass import Comment, Settings, build_ass, parse_time, read_comments, schedule


class DanmakuTests(unittest.TestCase):
    def test_input_and_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.txt"
            path.write_text("\ufeff# comment\n0.5 hello, world\n00:02.25\t你好\n", encoding="utf-8")
            self.assertEqual(read_comments(path), [Comment(0.5, "hello, world"), Comment(2.25, "你好")])
            path.write_text("12\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Line 1"):
                read_comments(path)
        self.assertEqual(parse_time("01:02:03.25"), 3723.25)
        for invalid in ("nan", "inf", "-1", "1:60", "1:2:3:4"):
            with self.assertRaises(ValueError):
                parse_time(invalid)

    def test_distribution_mode_and_concentration(self):
        comments = [Comment(i, str(i)) for i in range(20000)]
        settings = Settings(10, 30, 16, concentration=24)
        times = [t for t, _ in schedule(comments, settings, random.Random(42))]
        bins = [sum(i <= t < i + 1 for t in times) for i in range(10, 30)]
        peak_midpoint = 10.5 + max(range(20), key=bins.__getitem__)
        self.assertLessEqual(abs(peak_midpoint - 16), 1.5)
        self.assertTrue(all(10 <= t <= 30 for t in times))
        wide = schedule(comments, Settings(10, 30, 16, concentration=2), random.Random(42))
        self.assertLess(sum(abs(t - 16) for t in times), sum(abs(t - 16) for t, _ in wide))

    def test_noise_changes_assignment_not_arrivals(self):
        comments = [Comment(i / 100, str(i)) for i in range(100)]
        clean = schedule(comments, Settings(10, 30, 16, noise=0), random.Random(3))
        noisy = schedule(comments, Settings(10, 30, 16, noise=10), random.Random(3))
        self.assertEqual([t for t, _ in clean], [t for t, _ in noisy])
        self.assertEqual([c for _, c in clean], comments)
        self.assertNotEqual([c for _, c in noisy], comments)
        self.assertCountEqual([c for _, c in noisy], comments)

    def test_ass_bounds_motion_seed_and_sanitizing(self):
        comments = [Comment(i, r"你好,{\pos(0,0)}\N") for i in range(200)]
        settings = Settings(10.003, 20.009, 17, screen_time=6)
        ass, _ = build_ass(comments, settings)
        self.assertEqual(build_ass(comments, settings)[0], ass)
        rows = [line for line in ass.splitlines() if line.startswith("Dialogue:")]
        self.assertEqual(len(rows), 200)
        heights = set()
        for row in rows:
            fields = row.split(",", 9)
            start, end = parse_time(fields[1]), parse_time(fields[2])
            self.assertGreaterEqual(start, settings.start)
            self.assertLessEqual(end, settings.end)
            self.assertGreater(end, start)
            motion = re.search(r"\\move\(([^)]+)\)", fields[9])
            x1, y1, x2, y2 = map(float, motion.group(1).split(","))
            self.assertGreater(x1, settings.width)
            self.assertLess(x2, x1)
            self.assertEqual(y1, y2)
            self.assertTrue(0 <= y1 < settings.height * settings.area)
            self.assertAlmostEqual((x1-x2)/(end-start), settings.width/settings.screen_time, delta=0.51)
            self.assertNotIn(r"\pos", fields[9])
            self.assertNotIn(r"\N", fields[9])
            heights.add(y1)
        self.assertGreater(len(heights), 10)

    def test_boundary_triggers_and_bad_settings(self):
        for trigger in (0, 1):
            ass, _ = build_ass([Comment(500, "x")], Settings(0, 1, trigger))
            self.assertIn("Dialogue:", ass)
        for settings in (Settings(5, 4, 4), Settings(0, 1, 2),
                         Settings(0, 1, 0.5, noise=-1),
                         Settings(0, 1, 0.5, concentration=float("nan")),
                         Settings(0, 0.001, 0), Settings(0, 1, 0.5, height=1)):
            with self.assertRaises(ValueError):
                settings.validate()


if __name__ == "__main__":
    unittest.main()
