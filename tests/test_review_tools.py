import contextlib
import importlib
import io
from pathlib import Path
import tempfile
import unittest

from yaoyao_review.common import configure


class ReviewToolTests(unittest.TestCase):
    def test_import_and_help_do_not_process_video(self):
        for name in ("scan", "analyze", "timeline", "review", "details", "make_collage"):
            module = importlib.import_module(f"yaoyao_review.{name}")
            with self.subTest(name=name), contextlib.redirect_stdout(io.StringIO()) as output:
                with self.assertRaises(SystemExit) as result:
                    module.main(["--help"])
                self.assertEqual(result.exception.code, 0)
                self.assertIn("--output-dir", output.getvalue())

    def test_missing_source_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            with contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as result:
                    configure("test", ["--source", str(Path(temporary) / "missing.mp4"),
                                       "--output-dir", str(output)], video=True)
            self.assertEqual(result.exception.code, 2)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
