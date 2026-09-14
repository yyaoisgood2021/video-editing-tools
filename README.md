# 视频剪辑工具集

用于制作滚动弹幕、渲染透明视频，以及复核游戏录像中的血条变化。

核心流程：`带时间戳的 TXT → 滚动 ASS → ProRes 4444 透明 MOV → 剪映上层轨道`。

## 环境准备

- Python 3.9 或更高版本。
- 弹幕和透明视频脚本仅使用 Python 标准库。
- 渲染需要 FFmpeg 和 ffprobe，FFmpeg 必须支持 `ass`、`unpremultiply` 滤镜和 `prores_ks` 编码器。
- 游戏分析额外需要 NumPy 和 Pillow：`python -m pip install -r requirements-review.txt`。

先用 `python --version` 确认解释器可以运行。Windows 也可使用 `py` 或实际安装的 Python 可执行文件路径。
FFmpeg 可加入 PATH，放在 `tools/ffmpeg/<解压目录>/bin/`，或通过 `--ffmpeg` 指定。
仓库不附带 FFmpeg、字体或原始录像。

## 快速开始

在仓库根目录执行：

```powershell
python danmaku_to_ass.py examples/example_danmaku.txt --start 10 --end 25 --trigger 16 -o demo.ass
python ass_to_video.py demo.ass --start 10 --end 25 -o demo.mov
```

将生成的 15 秒 `demo.mov` 放在剪映原视频第 **10 秒**的上层轨道。
已有输出不会被覆盖；重新生成时添加 `--force`。

TXT 每行是一条“时间 + 空格 + 弹幕内容”，使用 UTF-8 编码：

```text
0.5 前方高能
00:02.100 来了来了
00:00:03.200 哈哈哈，太强了
```

源时间影响弹幕顺序；脚本会将全部弹幕重新安排到目标时间窗口。
`--trigger` 控制新弹幕到达概率的峰值，不代表每条弹幕的原始同步时间。

## 目录和文档

| 路径 | 用途 |
| --- | --- |
| `danmaku_to_ass.py` | TXT 转带移动动画的 ASS |
| `ass_to_video.py` | ASS 转带 Alpha 通道的 MOV |
| `yaoyao_review/` | 血条抽帧、候选检测、复核图和拼图脚本 |
| `examples/` | 小型输入样例及对应 ASS |
| `tests/` | 弹幕规则、透明视频和工具配置测试 |
| `docs/` | 参数说明、工作流程及原录像复核记录 |
| `.github/workflows/tests.yml` | GitHub Actions 自动测试 |

- [弹幕时间分布与外观参数](docs/danmaku.md)
- [透明视频渲染、导入与排错](docs/transparent-video.md)
- [游戏血条分析和拼图](docs/game-review.md)
- [原录像的 12 次血条变空窗口](docs/死亡时间窗口.md)
- [开发和验证说明](CONTRIBUTING.md)

## 测试

```powershell
python -m unittest discover -s tests -v
```

找不到 FFmpeg 时，透明视频集成测试会跳过；安装了不兼容的 FFmpeg 时会报错。
集成测试实际渲染小视频，检查 Alpha、颜色、移动轨迹、裁切和输出保护。

## 使用边界

- 弹幕轨道采用近似文字宽度，密集时可能重叠，脚本会提示。
- 直接导入 ASS 是否保留动画取决于剪映版本；当前未验证剪映内的 ASS 或透明 MOV 导入效果。
- 游戏分析针对特定录像的 HUD 坐标和时间窗口，迁移到其他录像前需要调整，候选结果仍需人工复核。
- 原视频、MOV、NumPy 缓存、抽帧图片和封面草稿留在本地，由 `.gitignore` 排除；代码、文档和小型样例纳入版本管理。

项目尚未指定开源许可证。
