[中文文档](README.zh-CN.md)

# Standalone ESRGAN Video Upscale

A lightweight Gradio frontend for video upscaling: loads ESRGAN-class models via spandrel and upscales **frame-by-frame in a streaming pipeline**, keeping system RAM nearly constant — suited to low-VRAM / low-memory setups.

## Credits

The core idea comes from [this article](https://ai-hardware-zukan.com/en/comfyui-standalone-esrgan-video-4k-upscale-en/) (the author calls ESRGAN models through spandrel for streaming, low-memory video upscaling). This project implements, packages, and GUI-wraps that approach.

## Features

- Gradio Web UI: upload a video, pick a model, tune tile size, watch progress and results
- Streaming decode → tile upscale → encode, with a bounded queue to limit peak memory
- Automatic audio extract and mux
- Adjustable tile size (lower it when VRAM is tight)

## Requirements

- Python 3.10+ (recommended)
- NVIDIA GPU + CUDA (default `cuda:0`)
- System `ffmpeg` / `ffprobe`
- Python packages in `requirements.txt`

```bash
pip install -r requirements.txt
```

## Prepare models

By default models are loaded from the ComfyUI upscale models folder (change `MODEL_DIR` in `gui.py` if needed):

```text
~/ComfyUI/models/upscale_models/
```

If you do not have the following models locally, download them from the links below into that folder:

| Model | Hugging Face |
|---|---|
| `4x-AnimeSharp.pth` | [Kim2091/AnimeSharp](https://huggingface.co/Kim2091/AnimeSharp/blob/main/4x-AnimeSharp.pth) |
| `4x_NMKD-Siax_200k.pth` | [uwg/upscaler](https://huggingface.co/uwg/upscaler/blob/main/ESRGAN/4x_NMKD-Siax_200k.pth) |
| `4x_foolhardy_Remacri.pth` | [FacehugmanIII/4x_foolhardy_Remacri](https://huggingface.co/FacehugmanIII/4x_foolhardy_Remacri/blob/main/4x_foolhardy_Remacri.pth) |
| `RealESRGAN_x2plus.pth` | [2kpr/Real-ESRGAN](https://huggingface.co/2kpr/Real-ESRGAN/blob/main/RealESRGAN_x2plus.pth) |

Other `.pth` / `.safetensors` upscalers in the same folder are also supported.

## Tested environment

| Item | Version / notes |
|---|---|
| OS | Ubuntu 26.04.1 LTS |
| Python | 3.11.15 |
| GPU | NVIDIA GeForce RTX 5080 (16 GB) |
| CUDA (PyTorch) | 13.0 |
| torch | 2.13.0+cu130 |
| numpy | 2.3.2 |
| spandrel | 0.4.2 |
| gradio | 6.22.0 |
| Pillow | 12.3.0 |
| OpenCV | 5.0.0 |
| ffmpeg / ffprobe | 8.0.1 |

## Run

```bash
python gui.py
```

Open `http://127.0.0.1:7860` in a browser (listens on `0.0.0.0:7860` by default).

Outputs are written under `output/` (gitignored).

## Project layout

```text
esrgan-upscale/
├── engine.py          # streaming upscale core (ffprobe/ffmpeg + spandrel tiling)
├── gui.py             # Gradio UI
├── requirements.txt
├── README.md
├── README.zh-CN.md
└── output/            # local outputs (gitignored)
```

## Tips

| Item | Notes |
|---|---|
| Tile | Default `768`; try `512` / `384` on OOM |
| Device | `engine.upscale_video(..., device="cuda:0")` |
| Encode | H.264, `crf=10`, `preset=medium` |

## License

**MIT**

Please also follow the terms of any ESRGAN models you load and of the upstream article.
