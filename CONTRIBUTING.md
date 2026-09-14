# 开发和验证

核心脚本保留在根目录，游戏分析工具集中在 `yaoyao_review/`。
命令行入口位于 `main()`；导入分析模块不会启动抽帧或读写缓存。

## 本地检查

```powershell
python -m unittest discover -s tests -v
python danmaku_to_ass.py --help
python ass_to_video.py --help
python -m yaoyao_review.scan --help
```

弹幕和透明视频测试依赖标准库及 FFmpeg。分析数据流程另需安装 `requirements-review.txt`。
修改渲染逻辑后，应安装完整 FFmpeg 并确认集成测试实际执行，不能只依据跳过后的绿色结果。

自动测试覆盖弹幕时间边界、随机可复现性、文字转义、透明通道、颜色、移动、裁切和文件覆盖保护。
实际死亡判定和最终拼图需要对源视频人工复核。

## 提交范围

- 提交源码、测试、Markdown 文档、依赖声明和精选小型样例。
- 不提交凭据、个人绝对路径、第三方程序、原始录像、渲染视频或分析缓存。
- 使用 `git status --short` 和 `git diff --cached --stat` 检查提交内容。
- 改变参数、输出路径或时间语义时，同步更新文档。

GitHub Actions 在 Python 3.9 和 3.12 下运行测试，并安装 FFmpeg 执行透明视频集成测试。
