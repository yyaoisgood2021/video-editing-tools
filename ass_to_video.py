#!/usr/bin/env python3
"""Render UTF-8 ASS animations into a transparent ProRes 4444 MOV.

Python 3.9+ standard library; requires FFmpeg with libass and ffprobe.
Output time zero corresponds to --start on the original ASS timeline.
"""

import argparse
from fractions import Fraction
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


def seconds(value):
    value = str(value).strip()
    if not re.fullmatch(r"\d+(?::\d{1,2}){0,2}(?:\.\d+)?", value):
        raise ValueError(f"Invalid timestamp: {value!r}")
    parts = [float(p) for p in value.split(":")]
    if len(parts) > 1 and any(p >= 60 for p in parts[1:]):
        raise ValueError(f"Invalid timestamp: {value!r}")
    result = 0.0
    for part in parts:
        result = result * 60 + part
    if not math.isfinite(result):
        raise ValueError("Timestamp must be finite")
    return result


def inspect_ass(path):
    """Read resolution and event intervals; leave all animation tags untouched."""
    content = Path(path).read_text(encoding="utf-8-sig")
    resolution = {}
    intervals = []
    section = ""
    fields = None
    for number, raw in enumerate(content.splitlines(), 1):
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line.lower()
            fields = None
            continue
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key = key.strip().lower()
        if section == "[script info]" and key in ("playresx", "playresy"):
            resolution[key] = int(value.strip())
        elif section == "[events]" and key == "format":
            fields = [v.strip().lower() for v in value.split(",")]
            if not {"start", "end", "text"}.issubset(fields) or fields[-1] != "text":
                raise ValueError("ASS Events Format must include Start/End and end with Text")
        elif section == "[events]" and key == "dialogue":
            if not fields:
                raise ValueError(f"Line {number}: Dialogue before Events Format")
            values = value.split(",", len(fields) - 1)
            if len(values) != len(fields):
                raise ValueError(f"Line {number}: malformed Dialogue")
            row = dict(zip(fields, values))
            start, end = seconds(row["start"]), seconds(row["end"])
            if end <= start:
                raise ValueError(f"Line {number}: event end must exceed start")
            intervals.append((start, end))
    if not intervals:
        raise ValueError("ASS contains no Dialogue events")
    return content, resolution, intervals


def find_ffmpeg(explicit=None):
    if explicit:
        candidate = shutil.which(str(explicit)) or str(Path(explicit).resolve())
        if not Path(candidate).is_file():
            raise ValueError(f"FFmpeg not found: {explicit}")
        return Path(candidate).resolve()
    root = Path(__file__).resolve().parent
    for candidate in (root / "tools" / "ffmpeg.exe", root / "tools" / "ffmpeg"):
        if candidate.is_file():
            return candidate
    candidates = sorted((root / "tools" / "ffmpeg").glob("*/bin/ffmpeg.exe"))
    if candidates:
        return candidates[-1].resolve()
    found = shutil.which("ffmpeg")
    if found:
        return Path(found).resolve()
    raise ValueError("FFmpeg not found. Install a libass-enabled build or pass --ffmpeg PATH")


def run_capture(command, **kwargs):
    result = subprocess.run([str(v) for v in command], capture_output=True, **kwargs)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace")
        raise ValueError(f"FFmpeg/ffprobe failed:\n{detail[-6000:]}")
    return result.stdout


def check_dependencies(ffmpeg, explicit_probe=None):
    for kind, name in (("filter", "ass"), ("filter", "unpremultiply"),
                       ("encoder", "prores_ks")):
        result = subprocess.run([str(ffmpeg), "-hide_banner", "-h", f"{kind}={name}"],
                                capture_output=True)
        message = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        if result.returncode or "Unknown" in message or "not recognized" in message:
            raise ValueError(f"This FFmpeg lacks {kind} {name}; use a full libass-enabled build")
    probe = Path(explicit_probe).resolve() if explicit_probe else ffmpeg.with_name(
        "ffprobe.exe" if os.name == "nt" else "ffprobe")
    if not probe.is_file():
        found = shutil.which("ffprobe") if not explicit_probe else None
        if not found:
            raise ValueError("ffprobe not found beside FFmpeg; pass --ffprobe PATH")
        probe = Path(found).resolve()
    return probe


def make_command(ffmpeg, width, height, fps, frames, start, quality, threads, fonts=False,
                 alpha_metadata=False):
    # The ASS is copied to a safe relative filename in a private work directory.
    # This avoids FFmpeg filter escaping issues with Windows drive letters,
    # Chinese characters, apostrophes, spaces, brackets, and commas in paths.
    subtitle_filter = "ass=filename=input.ass"
    if fonts:
        subtitle_filter += ":fontsdir=fonts"
    # New FFmpeg versions negotiate alpha representation between filters.
    # Mark the recovered black RGB as premultiplied before unpremultiplication,
    # otherwise automatic conversion can cancel the correction.
    mark_premult = "setparams=alpha_mode=premultiplied," if alpha_metadata else ""
    output_format = "yuva444p10le" + (":alpha_modes=straight" if alpha_metadata else "")
    filters = (
        f"[0:v]settb=AVTB,setpts=PTS+{start:.9f}/TB,split=2[baseb][basew];"
        f"[baseb]{subtitle_filter},format=gbrp,split=2[black][blackmask];"
        f"[basew]lutrgb=r=255:g=255:b=255,{subtitle_filter},format=gbrp[white];"
        "[white][blackmask]blend=all_mode=subtract,negate,extractplanes=r[alpha];"
        f"[black][alpha]alphamerge,format=gbrap,{mark_premult}unpremultiply=inplace=1:planes=7,"
        "setpts=PTS-STARTPTS,"
        f"scale=out_color_matrix=bt709:out_range=tv,format={output_format}[out]"
    )
    # Render identically over opaque black and white. Their difference is 1-A;
    # black contains premultiplied RGB. This avoids FFmpeg ass:alpha=1 squaring
    # opacity on semi-transparent glyphs. Recover A, then straight RGB.
    return [str(ffmpeg), "-hide_banner", "-nostdin", "-n", "-filter_complex_threads", str(threads),
            "-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:r={fps},format=rgb24",
            "-filter_complex", filters, "-map", "[out]", "-frames:v", str(frames), "-an", "-c:v", "prores_ks",
            "-profile:v", "4", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16",
            "-qscale:v", str(quality), "-threads:v", str(threads),
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-color_range", "tv", "-movflags", "+faststart", "render.mov"]


def verify_movie(ffmpeg, probe, path, width, height, expected_frames, sample_time):
    info = json.loads(run_capture([probe, "-v", "error", "-select_streams", "v:0",
                                  "-show_streams", "-show_format", "-of", "json", path]))
    streams = info.get("streams", [])
    if not streams:
        raise ValueError("Rendered video has no video stream")
    video = streams[0]
    if video.get("codec_name") != "prores" or not video.get("pix_fmt", "").startswith("yuva"):
        raise ValueError(f"Rendered video does not have ProRes YUVA: {video.get('pix_fmt')}")
    if (video.get("width"), video.get("height")) != (width, height):
        raise ValueError("Rendered resolution differs from requested resolution")
    if int(video.get("nb_frames", 0)) != expected_frames:
        raise ValueError("Rendered frame count differs from requested frame count")
    raw = run_capture([ffmpeg, "-v", "error", "-ss", str(sample_time), "-i", path,
                       "-frames:v", "1", "-vf", "alphaextract,format=gray",
                       "-f", "rawvideo", "pipe:1"])
    if len(raw) != width * height:
        raise ValueError("Could not decode a complete alpha plane")
    return {"codec": video["codec_name"], "profile": video.get("profile"),
            "pixel_format": video["pix_fmt"], "width": width, "height": height,
            "frames": expected_frames, "duration": float(info["format"]["duration"]),
            "sample_time": sample_time, "alpha_min": min(raw), "alpha_max": max(raw),
            "transparent_pixels": raw.count(0),
            "nontransparent_pixels": len(raw) - raw.count(0)}


def render(args):
    source = args.input.resolve()
    output = (args.output or source.with_suffix(".mov")).resolve()
    if source == output or output.suffix.lower() != ".mov":
        raise ValueError("Output must be a separate .mov file")
    if output.exists() and not args.force:
        raise ValueError(f"Output exists: {output}; use --force to replace it")
    content, resolution, intervals = inspect_ass(source)
    start = seconds(args.start)
    end = seconds(args.end) if args.end is not None else max(b for _, b in intervals)
    if end <= start:
        raise ValueError("End must be greater than start")
    overlaps = [(max(start, a), min(end, b)) for a, b in intervals if a < end and b > start]
    if not overlaps:
        raise ValueError("No ASS events overlap the requested time window")
    width = args.width or resolution.get("playresx")
    height = args.height or resolution.get("playresy")
    if not width or not height or width <= 0 or height <= 0 or width % 2 or height % 2:
        raise ValueError("Use positive even width/height, or ASS PlayResX/PlayResY")
    fps = Fraction(args.fps)
    if not 0 < fps <= 240 or not 1 <= args.quality <= 31 or args.threads < 1:
        raise ValueError("Require 0 < fps <= 240, quality 1..31, threads >= 1")
    frames = math.ceil(Fraction(str(end - start)) * fps)
    ffmpeg = find_ffmpeg(args.ffmpeg)
    probe = check_dependencies(ffmpeg, args.ffprobe)
    help_result = subprocess.run([str(ffmpeg), "-hide_banner", "-h", "filter=setparams"],
                                 capture_output=True)
    alpha_metadata = b"alpha_mode" in help_result.stdout + help_result.stderr
    output.parent.mkdir(parents=True, exist_ok=True)
    # Use the output filesystem for staging and the final rename. Rendering or
    # verification failure leaves any previous output untouched.
    with tempfile.TemporaryDirectory(prefix=".ass-render-", dir=output.parent) as directory:
        work = Path(directory)
        (work / "input.ass").write_text(content, encoding="utf-8-sig")
        if args.fonts_dir:
            font_source = args.fonts_dir.resolve()
            if not font_source.is_dir():
                raise ValueError("--fonts-dir must be a directory")
            font_files = [p for p in font_source.iterdir()
                          if p.is_file() and p.suffix.lower() in (".ttf", ".otf", ".ttc")]
            if not font_files:
                raise ValueError("--fonts-dir has no TTF/OTF/TTC font files")
            (work / "fonts").mkdir()
            for index, font in enumerate(font_files):
                shutil.copyfile(font, work / "fonts" / f"font{index}{font.suffix.lower()}")
        command = make_command(ffmpeg, width, height, fps, frames, start,
                               args.quality, args.threads, bool(args.fonts_dir), alpha_metadata)
        print(f"Rendering {width}x{height}, {fps} fps, {frames} frames; ASS {start:g}..{end:g}s", flush=True)
        result = subprocess.run(command, cwd=work)
        if result.returncode:
            raise ValueError("FFmpeg rendering failed; see diagnostics above")
        a, b = max(overlaps, key=lambda interval: interval[1] - interval[0])
        sample_time = min(max(0, (a + b) / 2 - start), (frames - 1) / float(fps))
        report = verify_movie(ffmpeg, probe, work / "render.mov", width, height, frames, sample_time)
        if output.exists() and not args.force:
            raise ValueError("Output was created during rendering; refusing to overwrite")
        os.replace(work / "render.mov", output)
    report.update({"output": str(output), "place_at_seconds": start,
                   "size_mib": round(output.stat().st_size / 1024**2, 2)})
    print(json.dumps(report, ensure_ascii=True, indent=2))
    print(f"Place the MOV on the upper video track at {start:g} seconds. No chroma key needed.")
    if not report["transparent_pixels"] or not report["nontransparent_pixels"]:
        print("Note: sampled frame was fully opaque or fully transparent; inspect ASS content/visibility.")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 ASS file")
    parser.add_argument("-o", "--output", type=Path, help="ProRes 4444 MOV; default input.mov")
    parser.add_argument("--start", default="0", help="ASS timeline start; output begins at time zero")
    parser.add_argument("--end", help="ASS timeline end; default last event end")
    parser.add_argument("--fps", default="30", help="Frame rate, e.g. 30 or 30000/1001")
    parser.add_argument("--width", type=int, help="Default ASS PlayResX")
    parser.add_argument("--height", type=int, help="Default ASS PlayResY")
    parser.add_argument("--quality", type=int, default=9, help="ProRes quantizer 1..31; lower = larger/better")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--ffmpeg", help="Path to FFmpeg with libass")
    parser.add_argument("--ffprobe", help="Path to ffprobe; default beside FFmpeg")
    parser.add_argument("--fonts-dir", type=Path, help="Optional folder of TTF/OTF/TTC fonts")
    parser.add_argument("--force", action="store_true", help="Replace output only after successful rendering")
    args = parser.parse_args(argv)
    try:
        render(args)
    except (ValueError, OSError, ZeroDivisionError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    except KeyboardInterrupt:
        parser.exit(130, "Rendering cancelled\n")


if __name__ == "__main__":
    main()
