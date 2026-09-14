# 游戏血条分析和拼图

[返回首页](../README.md)

这些脚本记录了对 `9月11日.mp4` 的分析流程，原视频不在仓库中。
分析目标为右上角队伍列表中的血条，并跟踪目标在上下两行之间的切换。
“血条变空”是可见判据，不是通用死亡识别模型。

## 运行

在仓库根目录安装可选依赖，再抽帧、计算候选窗口和时间线：

```powershell
python -m pip install -r requirements-review.txt
python -m yaoyao_review.scan --source "D:/Videos/9月11日.mp4" --output-dir outputs/review
python -m yaoyao_review.analyze --output-dir outputs/review
python -m yaoyao_review.timeline --output-dir outputs/review
python -m yaoyao_review.review --output-dir outputs/review
```

复核固定窗口并制作拼图：

```powershell
python -m yaoyao_review.details --source "D:/Videos/9月11日.mp4" --output-dir outputs/review
python -m yaoyao_review.make_collage --source "D:/Videos/9月11日.mp4" --output-dir outputs/review
```

也支持 `python yaoyao_review/scan.py ...` 的直接调用方式。
需要视频的三个脚本都支持 `--ffmpeg "D:/ffmpeg/bin/ffmpeg.exe"`。
所有脚本支持 `--help` 和 `--output-dir`；默认输出到 `yaoyao_review/`，方便读取已有本地缓存。
重跑会覆盖同名派生图片和缓存，建议不同录像使用不同输出目录。

## 各阶段的数据

| 脚本 | 输入 | 输出 |
| --- | --- | --- |
| `scan.py` | 源录像 | 每秒 2 帧的 `roi.npy`、`overview_*.jpg` |
| `analyze.py` | `roi.npy` | `metrics.npz`、`candidate.json`、候选窗口图 |
| `timeline.py` | `roi.npy`、`metrics.npz` | `timeline_*.png`，覆盖全部缓存时长 |
| `review.py` | `roi.npy` | 固定复核窗口的 `review_*.jpg` |
| `details.py` | 源录像 | 固定窗口按 24 fps 解码的数组、联系表和全画面截图 |
| `make_collage.py` | 源录像 | `collage_frames/`、带时间标签的 3 列 4 行全图和 HUD 拼图 |

`candidate.json` 保存每秒 2 帧缓存中的 `[开始索引, 结束索引)`；除以 2 才是秒。
候选窗口与人工确认的 [12 次时间窗口](死亡时间窗口.md) 不是同一份结果。

## 适配其他录像

1. 抽帧使用 `crop=140:106:1000:74`，要求画面覆盖该坐标区域。
2. `analyze.py` 的名字模板、两行血条坐标和颜色阈值针对原录像。
3. `review.py`、`details.py` 的 `ranges`，以及 `make_collage.py` 的 `times` 是人工选定的固定时间。
4. 拼图还使用 `crop=1030:710:125:4`；更改分辨率后需调整构图。
5. 拼图需要带 `drawtext` 及字体发现支持的 FFmpeg，默认使用 Arial；缺少字体时安装字体或修改脚本中的字体名称。

抽帧缓存保存在内存中。长录像需要足够内存；可先截取相关片段，但应同步调整固定时间窗口。
脚本不修改源视频，也不自动从候选检测生成最终结论。
