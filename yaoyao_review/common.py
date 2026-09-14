"""Shared command-line configuration for the recording-specific review tools."""

import argparse
from pathlib import Path
import sys

# Support both `python -m yaoyao_review.scan` and direct script invocation.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ass_to_video import find_ffmpeg


def configure(description, argv=None, *, video=False):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent,
                        help="Directory for extracted frames, caches and reports")
    if video:
        parser.add_argument("--source", type=Path, required=True, help="Source recording")
        parser.add_argument("--ffmpeg", help="FFmpeg executable; default automatic discovery")
    args = parser.parse_args(argv)
    if video:
        if not args.source.is_file():
            parser.error(f"Source video not found: {args.source}")
        args.source = args.source.resolve()
        try:
            args.ffmpeg = find_ffmpeg(args.ffmpeg)
        except ValueError as exc:
            parser.error(str(exc))
    args.output_dir = args.output_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    return args
