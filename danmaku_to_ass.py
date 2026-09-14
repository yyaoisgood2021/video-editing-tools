#!/usr/bin/env python3
"""Retiming timestamped UTF-8 text into a trigger-centred scrolling ASS burst.

Standard library only, Python 3.9+. See README.md for timing semantics.
"""

import argparse
from dataclasses import dataclass
import math
from pathlib import Path
import random
import re
import sys
import unicodedata


def parse_time(value):
    """Accept nonnegative seconds, MM:SS, or HH:MM:SS (fractional seconds)."""
    value = str(value).strip()
    if not re.fullmatch(r"\d+(?::\d{1,2}){0,2}(?:\.\d+)?", value):
        raise ValueError(f"Invalid time: {value!r}")
    parts = [float(p) for p in value.split(":")]
    if len(parts) > 1 and any(p >= 60 for p in parts[1:]):
        raise ValueError(f"Minutes/seconds must be below 60: {value!r}")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    if not math.isfinite(seconds):
        raise ValueError("Time must be finite")
    return seconds


@dataclass(frozen=True)
class Comment:
    time: float
    text: str


@dataclass(frozen=True)
class Settings:
    start: float
    end: float
    trigger: float
    concentration: float = 12.0
    noise: float = 0.75
    seed: int = 42
    width: int = 1920
    height: int = 1080
    font: str = "Microsoft YaHei"
    font_size: int = 42
    screen_time: float = 6.0
    area: float = 0.65

    def validate(self):
        values = (self.start, self.end, self.trigger, self.concentration,
                  self.noise, self.screen_time, self.area)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("All numeric settings must be finite")
        if not 0 <= self.start < self.end:
            raise ValueError("Require 0 <= start < end")
        if not self.start <= self.trigger <= self.end:
            raise ValueError("Trigger must be inside the window")
        if self.concentration <= 0 or self.noise < 0 or self.screen_time <= 0:
            raise ValueError("Concentration/screen-time must be positive; noise >= 0")
        if self.width < 1 or self.height < 1 or self.font_size < 1:
            raise ValueError("Resolution and font size must be positive")
        if not 0 < self.area <= 1:
            raise ValueError("Area must be in (0, 1]")
        if self.height * self.area < self.font_size * 1.5 + 16:
            raise ValueError("Selected height/area is too small for this font size")
        if not self.font.strip() or any(c in self.font for c in ",\r\n{}\\"):
            raise ValueError("Invalid font name")
        if math.floor(self.end * 100) - math.ceil(self.start * 100) < 2:
            raise ValueError("Window must contain at least two ASS centiseconds")


def read_comments(path):
    """One timestamp + whitespace + content per line; # lines are comments."""
    comments = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2 or not parts[1].strip():
            raise ValueError(f"Line {line_number}: expected TIME followed by text")
        try:
            timestamp = parse_time(parts[0])
        except ValueError as exc:
            raise ValueError(f"Line {line_number}: {exc}") from exc
        comments.append(Comment(timestamp, parts[1]))
    if not comments:
        raise ValueError("Input contains no comments")
    return comments


def schedule(comments, settings, rng):
    """Beta-distributed arrivals assigned in noisy source-time order.

    Mode of Beta(1+k*m, 1+k*(1-m)) is m, including boundary modes.
    Source times affect assignment/order, not the target arrival distribution.
    """
    settings.validate()
    if any(not math.isfinite(c.time) or c.time < 0 for c in comments):
        raise ValueError("Comment times must be finite and nonnegative")
    span = settings.end - settings.start
    mode = (settings.trigger - settings.start) / span
    alpha = 1 + settings.concentration * mode
    beta = 1 + settings.concentration * (1 - mode)
    arrivals = sorted(settings.start + span * rng.betavariate(alpha, beta)
                      for _ in comments)
    ranked = sorted(enumerate(comments), key=lambda item:
                    (item[1].time + rng.gauss(0, settings.noise), item[0]))
    return [(time, comment) for time, (_, comment) in zip(arrivals, ranked)]


def safe_text(text):
    # ASS has renderer-dependent literal brace escaping. Use visually similar
    # fullwidth characters so user text can never inject override/line-break tags.
    text = text.translate(str.maketrans({"{": "｛", "}": "｝", "\\": "＼"}))
    return " ".join("".join(c for c in text if unicodedata.category(c) != "Cc").split())


def estimate_width(text, size):
    # Conservative heuristic, not exact font shaping. Equal scrolling speed
    # prevents overtaking; font/emoji differences can still produce collisions.
    units = sum(0 if unicodedata.combining(c) else
                1.1 if unicodedata.east_asian_width(c) in "WFA" else 0.75
                for c in text)
    return math.ceil(max(1, units) * size + 8)


def ass_time(centiseconds):
    seconds, cs = divmod(centiseconds, 100)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"


def build_ass(comments, settings):
    """Return (ASS text, number of events forced onto occupied lanes)."""
    settings.validate()
    rng = random.Random(settings.seed)
    scheduled = schedule(comments, settings, rng)
    s = settings
    header = f"""[Script Info]
Title: Simulated danmaku
ScriptType: v4.00+
PlayResX: {s.width}
PlayResY: {s.height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Danmaku,{s.font},{s.font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&HFF000000,0,0,0,0,100,100,0,0,1,2,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lane_height = math.ceil(s.font_size * 1.5)
    lanes = max(1, int((s.height * s.area - 16) // lane_height))
    ready = [-math.inf] * lanes
    speed = s.width / s.screen_time
    first_cs = math.ceil(s.start * 100)
    last_cs = math.floor(s.end * 100)
    crowded = 0
    events = []
    for arrival, comment in scheduled:
        start_cs = max(first_cs, min(last_cs - 1, round(arrival * 100)))
        start = start_cs / 100
        text = safe_text(comment.text)
        if not text:
            raise ValueError("A comment has no visible text after sanitizing")
        text_width = estimate_width(text, s.font_size)
        # Small offscreen margin accommodates the outline.
        x_start = s.width + 4
        full_duration = (x_start + text_width + 4) / speed
        end_cs = min(last_cs, start_cs + max(1, math.ceil(full_duration * 100)))
        duration = (end_cs - start_cs) / 100
        x_end = x_start - speed * duration
        available = [lane for lane in range(lanes) if ready[lane] <= start]
        if available:
            lane = rng.choice(available)
        else:
            # Preserve all comments and their sampled times during crowded bursts.
            # Prefer the lane whose preceding text will clear first.
            lane = min(range(lanes), key=lambda i: ready[i])
            crowded += 1
        ready[lane] = max(ready[lane], start + (text_width + s.font_size) / speed)
        y = 8 + lane * lane_height + rng.uniform(0, s.font_size * 0.1)
        tags = (f"{{\\an7\\q2\\move({x_start},{y:.2f},{x_end:.2f},{y:.2f})"
                f"\\clip(0,0,{s.width},{s.height})}}")
        events.append(f"Dialogue: 0,{ass_time(start_cs)},{ass_time(end_cs)},"
                      f"Danmaku,,0,0,0,,{tags}{text}")
    return header + "\n".join(events) + "\n", crowded


def time_argument(value):
    try:
        return parse_time(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="UTF-8 TXT: TIME whitespace CONTENT")
    parser.add_argument("--start", type=time_argument, required=True, help="Absolute window start")
    parser.add_argument("--end", type=time_argument, required=True, help="Absolute hard stop")
    parser.add_argument("--trigger", type=time_argument, required=True, help="Peak arrival time")
    parser.add_argument("-o", "--output", type=Path, help="Default: input filename with .ass extension")
    parser.add_argument("--concentration", type=float, default=12, help="Higher = tighter burst (default 12)")
    parser.add_argument("--noise", type=float, default=0.75, help="Gaussian source-order jitter SD in seconds")
    parser.add_argument("--seed", type=int, default=42, help="Repeatable randomness (default 42)")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--font", default="Microsoft YaHei")
    parser.add_argument("--font-size", type=int, default=42)
    parser.add_argument("--screen-time", type=float, default=6, help="Seconds to travel one screen width")
    parser.add_argument("--area", type=float, default=0.65, help="Top fraction of frame used (0 < area <= 1)")
    parser.add_argument("--force", action="store_true", help="Replace an existing output")
    args = parser.parse_args(argv)
    output = args.output or args.input.with_suffix(".ass")
    try:
        if output.resolve() == args.input.resolve():
            raise ValueError("Output must not overwrite the input")
        if output.suffix.lower() != ".ass":
            raise ValueError("Output filename must end in .ass")
        settings = Settings(**{name: getattr(args, name) for name in Settings.__dataclass_fields__})
        comments = read_comments(args.input)
        result, crowded = build_ass(comments, settings)
        with output.open("w" if args.force else "x", encoding="utf-8-sig", newline="\n") as stream:
            stream.write(result)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Error: {exc}\n")
    print(f"Wrote {len(comments)} danmaku to {output}")
    print(f"Arrival-density mode: {args.trigger:g}s; hard stop: {args.end:g}s")
    if crowded:
        print(f"Note: {crowded} comments used occupied lanes; overlaps are possible.")
    print("ASS movement requires an ASS renderer; Jianying may discard animation on import.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
