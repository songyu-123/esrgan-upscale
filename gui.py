# gui.py
import os
import gradio as gr
from pathlib import Path
from engine import upscale_video

# ========== 配置区域（按你的实际路径修改） ==========
MODEL_DIR = Path.home() / "ComfyUI" / "models" / "upscale_models"   # 改成你的模型目录
OUTPUT_DIR = Path("./output")
OUTPUT_DIR.mkdir(exist_ok=True)
# ==================================================

def list_models():
    if not MODEL_DIR.exists():
        return []
    return sorted([f.name for f in MODEL_DIR.glob("*.pth")] + 
                  [f.name for f in MODEL_DIR.glob("*.safetensors")])

def run_upscale(input_path, model_name, tile, progress=gr.Progress()):
    if not input_path or not os.path.exists(input_path):
        raise gr.Error("请选择有效的视频文件")

    model_path = MODEL_DIR / model_name
    if not model_path.exists():
        raise gr.Error(f"模型不存在: {model_path}")

    filename = Path(input_path).stem + f"_4x_{Path(model_name).stem}.mp4"
    output_path = OUTPUT_DIR / filename

    def progress_cb(percent, message):
        progress(percent / 100, desc=message)

    try:
        result = upscale_video(
            src=input_path,
            dst=str(output_path),
            model_path=str(model_path),
            tile=int(tile),
            progress_callback=progress_cb
        )
        return str(result), f"成功！文件已保存到:\n{result}"
    except Exception as e:
        raise gr.Error(str(e))

with gr.Blocks(title="Standalone ESRGAN Video Upscale", theme=gr.themes.Soft()) as demo:
    gr.Markdown("## Standalone ESRGAN 视频放大（内存友好版）\n基于作者流式处理思路，系统内存几乎恒定")

    with gr.Row():
        with gr.Column(scale=2):
            input_video = gr.Video(label="输入视频（或直接拖路径）", sources=["upload"])
            # 也可以用下面这行改成纯路径输入（大文件更推荐）
            # input_path = gr.Textbox(label="视频完整路径", placeholder="/home/xxx/video.mp4")

            model_dd = gr.Dropdown(
                choices=list_models(),
                label="放大模型",
                value=list_models()[0] if list_models() else None
            )
            tile_slider = gr.Slider(256, 1280, value=768, step=64, label="Tile 大小（VRAM 不够就调小）")

            btn = gr.Button("开始放大", variant="primary")

        with gr.Column(scale=1):
            status = gr.Textbox(label="状态", lines=4)
            output_video = gr.Video(label="输出预览")
            output_path = gr.Textbox(label="输出路径")

    btn.click(
        fn=run_upscale,
        inputs=[input_video, model_dd, tile_slider],
        outputs=[output_path, status]
    ).then(
        fn=lambda p: p if p else None,
        inputs=output_path,
        outputs=output_video
    )

if __name__ == "__main__":
    demo.queue().launch(server_name="0.0.0.0", server_port=7860, share=False)