# 弹幕生成：TXT → ASS

[返回首页](../README.md)

下列命令均在仓库根目录执行。

Python 3.9+, standard library only. White text with black outline travels from
right to left. Random lanes occupy the top 65% of the frame by default.

## Run

```powershell
python danmaku_to_ass.py examples/example_danmaku.txt --start 10 --end 25 --trigger 16 -o examples/example_danmaku.ass
```

## Input

Save as UTF-8 `.txt`, one timestamp and comment per line, separated by spaces or
a tab. Blank lines and lines starting with `#` are ignored. Examples:

```text
0.5 前方高能
00:02.100 来了来了
00:00:03.200 哈哈哈，太强了
```

Timestamps accept seconds, `MM:SS.sss`, or `HH:MM:SS.sss`. Every input row is
included, even if its source timestamp is outside the target window. Malformed
rows produce an error with a line number.

## What the timing means

- `--start` / `--end`: absolute video timeline window. Every event starts inside
  it and ends by `--end`. Late comments can be cut off mid-scroll, at normal speed.
- `--trigger`: absolute time where the **arrival probability density** peaks.
  It is not a timeline offset. For the example, use the ASS timestamps as-is;
  do not shift the subtitles another 10 seconds.
- Source timestamps guide comment **order**, not exact final appearance times.
  This deliberate retiming allows the specified burst even if the input times
  originally follow a different distribution. Widely spaced comments can end
  up close together. This is unsuitable when exact source synchronization matters.
- `--noise 0.75`: add independent Gaussian noise with standard deviation 0.75
  seconds to each source timestamp before ordering. Larger noise shuffles nearby
  comments more; zero keeps chronological order, but arrivals remain randomized.
- `--concentration 12`: controls the burst shape. Larger values cluster arrivals
  more tightly around the trigger; smaller positive values spread them more evenly.
- `--seed 42`: same input/options/seed reproduce the same output. Change the seed
  to generate another variation.

Let `m = (trigger - start) / (end - start)` and `k = concentration`. Sample
`u ~ Beta(1 + k*m, 1 + k*(1-m))`, then `arrival = start + u*(end-start)`.
This distribution has its mode at the trigger, including at window boundaries.
Sort the sampled arrivals and assign comments in their noisy source-time order.
This retains the beta arrival distribution while letting source timestamps and
Gaussian jitter influence which text appears first.

The trigger describes the highest expected **new-arrival rate**, not a guarantee
that the largest finite-sample histogram bin or the most simultaneous visible
comments occurs at that exact instant. Small inputs vary considerably. Longer
scrolls usually make visible occupancy peak later. Near the window end, new
comments have little viewing time; leave several seconds after the trigger when
possible. ASS timestamps use centiseconds, so boundaries are rounded inward.

## Appearance

```powershell
python danmaku_to_ass.py examples/example_danmaku.txt --start 10 --end 25 --trigger 16 --concentration 24 --noise 1.5 --seed 7 --width 1920 --height 1080 --font-size 42 --area 0.8 --screen-time 5 -o burst.ass
```

`--screen-time` is the time to travel one frame width; smaller values scroll
faster. Long text needs additional time for its tail to leave the frame. All text
uses equal horizontal speed. Set the resolution to match your project.
`--font` defaults to `Microsoft YaHei`; install/select a suitable Chinese font.

Random free lanes and a small vertical jitter vary heights. The script estimates
text width to leave a horizontal gap. During crowded bursts it keeps every comment
at its sampled time, uses the earliest-clearing lane, and reports possible overlap.
This is not exact font shaping or Bilibili's full collision-avoidance engine.
Literal braces and backslashes become fullwidth lookalikes to prevent accidental
ASS commands. Other text, including commas and Chinese characters, is preserved.
Existing output files are protected unless you pass `--force`.

## 剪映 / Jianying compatibility

This produces standard ASS with `\move` animation and positioning. It cannot
force an editor to interpret those tags. Direct ASS import support and retention
of movement in your Jianying version have **not** been verified. An import that
produces static captions does not preserve the intended danmaku effect.

Check a short sample first. To preview the intended motion, use an ASS-capable
renderer such as Aegisub or libass. For the transparent-video workflow discussed
earlier, this ASS is the intermediate animation file: render it into a supported
alpha video, then import that video into Jianying. This script only creates ASS;
it does not create a transparent video or modify a Jianying project.

References: [ASS movement documentation](https://aeg-dev.github.io/AegiSite/docs/3.0/ASS_Tags/#movement),
[CapCut subtitle import help](https://www.capcut.com/help/how-to-import-subtitles).
The CapCut help page is not proof of Chinese Jianying animation compatibility.

## Tests

```powershell
python -m unittest discover -s tests -v
```

