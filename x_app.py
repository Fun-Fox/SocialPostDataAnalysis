import argparse

import gradio as gr
import os
import json
import subprocess
from dotenv import load_dotenv

SETTINGS_PATH = "./twitter_download/settings.json"
MAIN_SCRIPT_PATH = "./twitter_download/main.py"
# todo 需要优化存储路径等
# AUDIO_DIR = "social_data/twitter/relDonaldTrump/audio"
# 加载 HuggingFace Token
current_dir = os.path.dirname(os.path.abspath(__name__))
save_path = os.path.join(current_dir, "social_data/twitter")
load_dotenv()


def load_settings():
    with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_settings(
        save_path, user_lst, cookie,
        has_retweet, high_lights, likes,
        time_range, autoSync, down_log,
        image_format, has_video, log_output,
        max_concurrent_requests, proxy, md_output, media_count_limit
):
    settings = {
        "save_path": save_path,
        "user_lst": user_lst,
        "cookie": cookie,
        "has_retweet": has_retweet,
        "high_lights": high_lights,
        "likes": likes,
        "time_range": time_range,
        "autoSync": autoSync,
        "down_log": down_log,
        "image_format": image_format,
        "has_video": has_video,
        "log_output": log_output,
        "max_concurrent_requests": int(max_concurrent_requests),
        "proxy": proxy,
        "md_output": md_output,
        "media_count_limit": int(media_count_limit)
    }

    with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=4)

    return "✅ 配置已保存"


#
# def run_extraction(extract_path):
#     # settings = load_settings()
#     # video_dir = settings.get("save_path", ".")
#     video_dir = extract_path
#     if not os.path.exists(video_dir):
#         return f"❌ 视频路径不存在: {video_dir}"
#
#     audio_files = batch_extract_audio_from_directory(video_dir, AUDIO_DIR)
#     return f"✅ 已提取音频到 `{AUDIO_DIR}/`: \n" + "\n".join([os.path.basename(f) for f in audio_files])
#
#
# def get_audio_choices():
#     """获取 audio 目录下的所有音频文件"""
#     if not os.path.exists(AUDIO_DIR):
#         return []
#     return sorted([
#         os.path.join(AUDIO_DIR, f) for f in os.listdir(AUDIO_DIR)
#         if f.endswith(".mp3")
#     ])

#
# # 处理上传的音频文件列表
# def transcribe_and_diarize(audio_files: list, progress=gr.Progress()):
#     if not isinstance(audio_files, list):
#         audio_files = [audio_files]
#
#     progress(0, desc="开始处理...")
#     results = process_audio_files(
#         audio_files,
#         hf_token=HF_TOKEN,
#         device="cuda" if torch.cuda.is_available() else "cpu",
#         compute_type="float16" if torch.cuda.is_available() else "int8"
#     )
#
#     output = ""
#     for res in results:
#         output += f"\n\n📄 {res['audio_file']}:\n"
#         if 'error' in res:
#             output += f"❌ 错误: {res['error']}\n"
#         else:
#             for seg in res['result']:
#                 start = seg.get('start', 0)
#                 end = seg.get('end', 0)
#                 text = seg.get('text', '')
#                 speaker = seg.get('speaker', '未知')
#                 output += f"[{start:.2f}s - {end:.2f}s] [{speaker}] {text}\n"
#
#     return output


def run_crawler():
    try:
        result = subprocess.run(
            ["python", MAIN_SCRIPT_PATH],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        return result.stdout + "\n\n" + result.stderr
    except Exception as e:
        return f"❌ 运行失败: {str(e)}"


with gr.Blocks(title="🐦 Twitter 数据抓取配置与执行") as demo:
    gr.Markdown("## ⚙️ Twitter 抓取工具 - 设置 & 执行")

    with gr.Tab("🔧 编辑配置"):
        with gr.Row():
            save_path_textbox = gr.Textbox(
                label="保存路径",
                value=save_path,
                interactive=True
            )
            user_lst = gr.Textbox(label="用户名列表 (逗号分隔)", value=lambda: load_settings()['user_lst'])

        cookie = gr.Textbox(label="Cookie (auth_token 和 ct0)", value=lambda: load_settings()['cookie'], lines=2)

        with gr.Row():
            has_retweet = gr.Checkbox(label="包含转推", value=lambda: load_settings()['has_retweet'])
            high_lights = gr.Checkbox(label="仅下载 Highlights", value=lambda: load_settings()['high_lights'])
            likes = gr.Checkbox(label="下载点赞内容", value=lambda: load_settings()['likes'])

        with gr.Row():
            time_range = gr.Textbox(label="时间范围 (YYYY-MM-DD:YYYY-MM-DD)",
                                    value=lambda: load_settings().get('time_range', ''))
            autoSync = gr.Checkbox(label="自动同步已有内容", value=lambda: load_settings()['autoSync'])

        with gr.Row():
            down_log = gr.Checkbox(label="启用下载记录 (防重复)", value=lambda: load_settings()['down_log'])
            image_format = gr.Dropdown(choices=["orig", "jpg", "png"], label="图片格式",
                                       value=lambda: load_settings()['image_format'])
            has_video = gr.Checkbox(label="下载视频", value=lambda: load_settings()['has_video'])

        proxy = gr.Textbox(label="代理地址 (如 http://localhost:port)", value=lambda: load_settings()['proxy'])

        with gr.Row():
            log_output = gr.Checkbox(label="输出详细日志", value=lambda: load_settings()['log_output'])
            max_concurrent_requests = gr.Number(label="最大并发请求数",
                                                value=lambda: load_settings()['max_concurrent_requests'])

        md_output = gr.Checkbox(label="生成 Markdown 文件", value=lambda: load_settings()['md_output'])
        media_count_limit = gr.Number(label="Markdown 单文件媒体数限制",
                                      value=lambda: load_settings()['media_count_limit'])

        save_button = gr.Button("💾 保存设置")
        output = gr.Textbox(label="操作结果")

        save_button.click(
            fn=save_settings,
            inputs=[
                save_path_textbox,
                user_lst,
                cookie,
                has_retweet,
                high_lights,
                likes,
                time_range,
                autoSync,
                down_log,
                image_format,
                has_video,
                log_output,
                max_concurrent_requests,
                proxy,
                md_output,
                media_count_limit
            ],
            outputs=output
        )

    with gr.Tab("🚀 启动抓取"):
        log_output_box = gr.Textbox(label="运行日志", lines=20, max_lines=20)
        run_button = gr.Button("▶️ 开始抓取")
        run_button.click(fn=run_crawler, outputs=log_output_box)
        LOG_DIR = "./logs"


        def get_log_files():
            """获取 logs 目录下的所有日志文件"""
            if not os.path.exists(LOG_DIR):
                return []
            log_files = [f for f in os.listdir(LOG_DIR) if f.endswith('.log')]
            if not log_files:
                return None
            latest_log = max(log_files, key=lambda f: os.path.getmtime(os.path.join(LOG_DIR, f)))

            return os.path.join(LOG_DIR, latest_log)


        def read_latest_log_content():
            """读取指定日志内容，默认读取最新的"""
            log_files = get_log_files()
            if not log_files:
                return "⚠️ 当前无日志文件"
            selected = log_files
            with open(selected, "r", encoding="utf-8") as f:
                content = f.read()
            return content


        gr.Markdown("## 🕓 实时日志监控 / 查看历史日志")

        log_text = gr.Textbox(label="日志内容", value=read_latest_log_content, every=5, lines=10, max_lines=15)

    # with gr.Tab("🔊 提取帖子中视频的音频"):
    #     gr.Markdown("## 🎬 视频音频提取")
    #     extract_path = gr.Textbox(label="视频路径", )
    #     extract_btn = gr.Button("📁 提取 save_path 下视频的音频")
    #     extract_output = gr.Textbox(label="提取日志")
    #     extract_btn.click(fn=run_extraction, inputs=extract_path, outputs=extract_output)
    #
    # with gr.Tab("📝 语音识别转文本"):
    #     gr.Markdown("## 🗣️ WhisperX 文本+说话人识别")
    #
    #     with gr.Row():
    #         audio_selector = gr.Dropdown(choices=get_audio_choices(), label="选择已提取的音频文件", multiselect=True)
    #
    #     with gr.Row():
    #         audio_upload = gr.File(label="或者上传音频文件 (可多选)", file_types=[".mp3"])
    #         select_all_btn = gr.Button("✅ 全选音频文件")
    #         deselect_all_btn = gr.Button("❌ 清空选择")
    #
    #     stt_button = gr.Button("🗣️ 开始识别并分配说话人")
    #     output_text = gr.Textbox(label="识别结果", lines=25, max_lines=50)
    #
    #     selected_audios = gr.State([])  # 用作内部状态存储
    #
    #
    #     def select_all():
    #         choices = get_audio_choices()
    #         return gr.update(value=choices), choices
    #
    #
    #     def deselect_all():
    #         return gr.update(value=[]), []
    #
    #
    #     select_all_btn.click(fn=select_all, inputs=[], outputs=[audio_selector, selected_audios])
    #     deselect_all_btn.click(fn=deselect_all, inputs=[], outputs=[audio_selector, selected_audios])
    #
    #     audio_selector.change(fn=lambda x: x, inputs=audio_selector, outputs=selected_audios)
    #
    #     stt_button.click(
    #         fn=transcribe_and_diarize,
    #         inputs=[selected_audios],
    #         outputs=output_text
    #     )

if __name__ == "__main__":
    # os.makedirs(AUDIO_DIR, exist_ok=True)
    # 使用 argparse 解析命令行参数
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8186, help='Gradio 应用监听的端口号')
    args = parser.parse_args()

    if os.getenv('PLATFORM', '') == 'local':
        demo.launch(share=False, ssl_verify=False, ssl_certfile="cert.pem",
                    ssl_keyfile="key.pem",
                    allowed_paths=["tmp",
                                   os.path.join(os.getcwd(), 'logs')],
                    server_port=args.port, root_path="/tw-plugin")
    elif os.getenv('PLATFORM', '') == 'server':
        demo.launch(share=False, server_name="0.0.0.0", ssl_verify=False, ssl_certfile="cert.pem",
                    ssl_keyfile="key.pem",
                    allowed_paths=["tmp",
                                   os.path.join(os.getcwd(), 'Log')],
                    server_port=args.port, root_path="/tw-plugin")
