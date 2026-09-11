# Standalone ESRGAN Video Upscale

基于 Gradio 的轻量视频超分前端：用 spandrel 直接加载 ESRGAN 类模型，**流式逐帧**放大，系统内存占用几乎恒定，适合显存/内存紧张的环境。

## Credits / 致谢

核心思路来自 [这篇文章](https://ai-hardware-zukan.com/en/comfyui-standalone-esrgan-video-4k-upscale-en/)（作者通过 spandrel 直接调用 ESRGAN 模型，实现流式低内存视频放大）。本项目在此基础上进行了实现、封装和 GUI 化。

## 功能

- Gradio Web UI：上传视频、选模型、调 tile、看进度与结果
- 流式解码 → tile 放大 → 编码，队列限深，降低内存峰值
- 自动提取并回写音频
- Tile 大小可调（显存不够就调小）

## 依赖

- Python 3.10+（建议）
- NVIDIA GPU + CUDA（默认 `cuda:0`）
- 系统已安装 `ffmpeg` / `ffprobe`
- Python 包见 `requirements.txt`

```bash
pip install -r requirements.txt
```

## 准备模型

默认从 ComfyUI 的超分模型目录读取：

```text
~/ComfyUI/models/upscale_models/*.pth
~/ComfyUI/models/upscale_models/*.safetensors
```

可在 `gui.py` 里改 `MODEL_DIR`。

## 启动

```bash
python gui.py
```

浏览器打开 `http://127.0.0.1:7860`（默认监听 `0.0.0.0:7860`）。

输出默认写到项目下的 `output/`（该目录不会进仓库）。

## 项目结构

```text
esrgan-upscale/
├── engine.py          # 流式放大核心（ffprobe/ffmpeg + spandrel tile）
├── gui.py             # Gradio 前端
├── requirements.txt
├── README.md
└── output/            # 本地输出（已 gitignore）
```

## 参数提示

| 项 | 说明 |
|---|---|
| Tile | 默认 `768`；OOM 时降到 `512` / `384` |
| 设备 | `engine.upscale_video(..., device="cuda:0")` |
| 编码 | H.264，`crf=10`，`preset=medium` |

## License

未单独声明许可证；使用前请同时遵守所加载 ESRGAN 模型与上游文章相关约定。
