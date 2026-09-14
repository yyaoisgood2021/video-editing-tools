# ASS → 透明弹幕视频

[返回首页](../README.md)

下列命令均在仓库根目录执行。

`ass_to_video.py` 使用 FFmpeg/libass 渲染真正的 ASS 动画，输出带 Alpha
通道的 **ProRes 4444 MOV**。不需要抠绿幕，不会把透明背景变成黑底。
Python 部分不需要安装第三方包；需要支持 `ass`、`unpremultiply` 滤镜和
`prores_ks` 编码器的 FFmpeg，以及同目录的 ffprobe。

FFmpeg 需要自行安装，不随仓库分发。支持 PATH、项目内 `tools/ffmpeg/`，
或 `--ffmpeg` / `--ffprobe` 指定可执行文件路径。脚本不会自动下载软件。

运行示例：

```powershell
python ass_to_video.py examples/example_danmaku.ass --start 10 --end 25 -o example_danmaku_alpha.mov
```

- `--start 10 --end 25`：渲染 ASS 原时间轴的 10–25 秒，得到 **15 秒**视频。
  放到剪映原视频 **第 10 秒**的上方视频轨道，保持原尺寸、位置和 100% 不透明度。
  原样例第一条弹幕在原视频约 13.14 秒出现，也就是素材内约 3.14 秒。
- 不传时间参数：从 ASS 第 0 秒渲染到最后一条结束，导入后放到时间轴第 0 秒。
- 裁切时不重新计算或重置 ASS 动画。跨越裁切起点的弹幕会从原本的位置继续移动。
- 分辨率默认读取 `PlayResX/PlayResY`；可传 `--width 1920 --height 1080`。
- `--fps 30`：默认 30 帧，也支持 `60`、`30000/1001` 等。总时长按整帧向上取整，
  最多比指定时长长不到一帧。
- `--quality 9`：默认质量，数值越小画质越高、文件通常越大，范围 1–31。
- `--fonts-dir 文件夹`：可选，提供额外 TTF/OTF/TTC 字体；默认使用系统字体。
- `--force`：允许替换已有 MOV，但仅在新视频成功渲染并通过检查后替换。

输出无音频，白字、黑色描边和其他 ASS 样式都由 libass 渲染。
脚本分别在纯黑和纯白背景渲染相同 ASS，通过两次结果的差恢复 Alpha，
再转回 straight alpha。这避免本机 FFmpeg `ass:alpha=1` 对半透明内容
产生透明度平方的问题，也避免文字边缘在叠加时被重复压暗。
编码后检查分辨率、帧数、像素格式，并解码
一帧检查实际 Alpha 像素。抽样不等于逐帧视觉检查。

已生成的 1920×1080、30 fps、15 秒样例约 **36.77 MiB**。
这是中间素材大小；最终合成 MP4 的大小仍主要取决于最终导出码率。
普通播放器可能把透明区域显示为黑色，不能据此判断透明通道丢失。
在剪映中把 MOV 叠在原视频上检查；如果仍显示黑色矩形，则需要核对该版本
对 ProRes 4444 Alpha 的处理。当前已验证文件本身的透明通道，未验证剪映导入。

实现参考：[FFmpeg ASS/Alpha 滤镜文档](https://ffmpeg.org/ffmpeg-filters.html#ass)、
[ProRes 编码器参数](https://ffmpeg.org/ffmpeg-codecs.html#ProRes)。
