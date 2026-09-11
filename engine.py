# engine.py
import os
import json
import subprocess
import threading
import queue
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import torch
import spandrel
from spandrel import ImageModelDescriptor

def get_video_info(path: str):
    """用 ffprobe 获取宽高、fps、总帧数"""
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames,duration",
        "-of", "json", path
    ]
    out = subprocess.check_output(cmd, text=True)
    info = json.loads(out)["streams"][0]

    w = int(info["width"])
    h = int(info["height"])

    # fps
    num, den = map(int, info["r_frame_rate"].split("/"))
    fps = num / den if den else 30

    # 总帧数
    if "nb_frames" in info and info["nb_frames"].isdigit():
        total = int(info["nb_frames"])
    else:
        duration = float(info.get("duration", 0))
        total = int(duration * fps) if duration else 0

    return w, h, fps, total

def load_model(model_path: str, device: str = "cuda:0"):
    loader = spandrel.ModelLoader(device=device)
    loaded = loader.load_from_file(model_path)
    if not isinstance(loaded, ImageModelDescriptor):
        raise ValueError(f"不支持的模型类型: {type(loaded)}")
    model = loaded.model.eval().half().to(device)
    scale = loaded.scale
    return model, scale

def upscale_frame(img: torch.Tensor, model, tile: int = 768, pad: int = 32, scale: int = 4):
    """单帧 tile 放大（作者核心逻辑）"""
    _, _, H, W = img.shape
    if H <= tile and W <= tile:
        with torch.inference_mode():
            return model(img)

    out = torch.zeros((1, 3, H * scale, W * scale), dtype=img.dtype, device=img.device)

    for y in range(0, H, tile):
        for x in range(0, W, tile):
            ys = max(y - pad, 0)
            xs = max(x - pad, 0)
            ye = min(y + tile + pad, H)
            xe = min(x + tile + pad, W)

            with torch.inference_mode():
                up = model(img[:, :, ys:ye, xs:xe])

            top = (y - ys) * scale
            left = (x - xs) * scale
            dy = y * scale
            dx = x * scale
            h = min(tile, H - y) * scale
            w = min(tile, W - x) * scale

            out[:, :, dy:dy + h, dx:dx + w] = up[:, :, top:top + h, left:left + w]

    return out

def upscale_video(
    src: str,
    dst: str,
    model_path: str,
    tile: int = 768,
    pad: int = 32,
    device: str = "cuda:0",
    progress_callback: Optional[Callable[[float, str], None]] = None,
):
    """
    流式放大主函数
    progress_callback(percent: float, message: str)
    """
    src = str(src)
    dst = str(dst)
    os.makedirs(os.path.dirname(dst) or ".", exist_ok=True)

    # 1. 加载模型
    if progress_callback:
        progress_callback(0, "正在加载模型...")
    model, scale = load_model(model_path, device)

    # 2. 获取视频信息
    W, H, fps, total_frames = get_video_info(src)
    if total_frames == 0:
        raise RuntimeError("无法获取视频总帧数")

    out_w, out_h = W * scale, H * scale
    frame_bytes = W * H * 3

    # 临时无音频文件和无声视频
    tmp_video = dst + ".tmp.mp4"
    tmp_audio = dst + ".tmp.aac"

    # 3. 提取音频（尽量无损复制）
    if progress_callback:
        progress_callback(1, "正在提取音频...")
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", src,
            "-vn", "-c:a", "copy", "-f", "adts", tmp_audio
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        has_audio = True
    except Exception:
        has_audio = False

    # 4. 启动解码和编码管道
    dec = subprocess.Popen([
        "ffmpeg", "-i", src,
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-v", "error", "pipe:1"
    ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)

    enc = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{out_w}x{out_h}", "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264", "-crf", "10", "-preset", "medium",
        "-pix_fmt", "yuv420p",
        tmp_video
    ], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    q = queue.Queue(maxsize=8)  # 限制内存，作者原版是 64，这里更保守

    def reader():
        while True:
            buf = dec.stdout.read(frame_bytes)
            if len(buf) < frame_bytes:
                break
            frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3).copy()
            q.put(frame)
        q.put(None)

    threading.Thread(target=reader, daemon=True).start()

    # 5. 逐帧处理
    processed = 0
    start_time = time.time()

    while True:
        frame = q.get()
        if frame is None:
            break

        t = torch.from_numpy(frame).to(device).half().permute(2, 0, 1)[None] / 255.0
        up = upscale_frame(t, model, tile=tile, pad=pad, scale=scale)
        out = (up[0].permute(1, 2, 0).clamp(0, 1) * 255).byte().cpu().numpy()
        enc.stdin.write(out.tobytes())

        processed += 1
        if progress_callback and processed % 5 == 0:  # 每 5 帧回调一次
            percent = min(99.0, processed / total_frames * 100)
            elapsed = time.time() - start_time
            eta = (elapsed / processed) * (total_frames - processed) if processed > 0 else 0
            progress_callback(
                percent,
                f"处理中 {processed}/{total_frames} 帧 | ETA {eta:.0f}s"
            )

    enc.stdin.close()
    enc.wait()
    dec.wait()

    # 6. 合成最终文件（带音频）
    if progress_callback:
        progress_callback(99.5, "正在合成最终视频...")

    if has_audio and os.path.exists(tmp_audio):
        subprocess.run([
            "ffmpeg", "-y",
            "-i", tmp_video, "-i", tmp_audio,
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", dst
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(tmp_audio)
    else:
        os.rename(tmp_video, dst)

    if os.path.exists(tmp_video):
        os.remove(tmp_video)

    if progress_callback:
        progress_callback(100, f"完成！输出: {dst}")

    return dst