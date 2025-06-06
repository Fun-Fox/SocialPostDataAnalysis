import whisperx  # WhisperX 是一个支持语音识别和说话人分割的库
import os
import torch
import gc
from typing import List, Dict, Union


# 配置路径
def extract_audio(video_path: str, audio_dir: str = "audio") -> str | None:
    """
    从视频文件中提取音频并保存为 MP3 格式
    :param video_path: 视频文件路径
    :param audio_dir: 提取后的音频保存目录
    :return: 返回音频文件路径或 None（失败时）
    """
    os.makedirs(audio_dir, exist_ok=True)
    video_name = os.path.splitext(os.path.basename(video_path))[0]  # 获取不带扩展名的视频文件名
    audio_file = os.path.join(audio_dir, f"{video_name}.mp3")  # 构建输出音频文件路径

    if os.path.exists(audio_file):
        return audio_file  # 如果已经存在该音频，则直接返回路径

    try:
        from moviepy import VideoFileClip
        clip = VideoFileClip(video_path)  # 加载视频文件
        if clip.audio is None:
            raise ValueError("该视频文件没有音频轨道")
        clip.audio.write_audiofile(audio_file)  # 写入音频文件
        print(f"音频提取完成: {audio_file}")
        return audio_file
    except Exception as e:
        print(f"❌ 提取音频失败 ({video_path}): {str(e)}")
        return None


def batch_extract_audio_from_directory(video_dir: str, audio_dir: str = "audio"):
    """
    批量提取指定目录下所有视频的音频
    :param video_dir: 视频文件夹路径
    :param audio_dir: 音频保存路径
    :return: 提取成功的音频文件路径列表
    """
    supported_exts = ['.mp4', '.mkv', '.avi', '.mov']  # 支持的视频格式
    video_files = [
        os.path.join(video_dir, f)
        for f in os.listdir(video_dir)
        if os.path.splitext(f)[1].lower() in supported_exts
    ]

    for video_file in video_files:
        print(f"🎵 正在提取 {video_file} 的音频...")
        extract_audio(video_file, audio_dir)

    print(f"✅ 已提取全部音频到 {audio_dir}")

    return [os.path.join(audio_dir, f"{os.path.splitext(os.path.basename(vf))[0]}.mp3") for vf in video_files]


# 主处理函数
def process_audio_files(audio_paths: Union[str, List[str]], hf_token: str, device="cuda", compute_type="float16",
                        batch_size=16):
    """
    处理多个音频文件：语音识别 + 时间对齐 + 说话人分配
    :param audio_paths: 单个或多个音频文件路径
    :param hf_token: HuggingFace 认证 Token
    :param device: 使用设备 ('cuda' 或 'cpu')
    :param compute_type: 模型计算类型 (float16 / int8)# change to "int8" if low on GPU mem (may reduce accuracy)
    :param batch_size: 批处理大小
    :return: 包含识别结果的列表
    """
    results = []

    if isinstance(audio_paths, str):
        audio_paths = [audio_paths]

    for audio_file in audio_paths:
        print(f"🔄 处理音频文件: {audio_file}")
        try:
            # 第一步：加载 WhisperX 模型并转录音频
            # model = whisperx.load_model("large-v2", device, compute_type=compute_type)
            # save model to local path (optional)
            model_dir = "/path/"
            model = whisperx.load_model("large-v2", device, compute_type=compute_type, download_root=model_dir)

            audio = whisperx.load_audio(audio_file)
            result = model.transcribe(audio, batch_size=batch_size)
            print(result["segments"])  # 输出初步识别结果

            # 清理模型以释放 GPU 显存（可选）
            # del model
            # gc.collect()
            # torch.cuda.empty_cache()

            # 第二步：对识别结果进行时间戳对齐
            model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
            result = whisperx.align(result["segments"], model_a, metadata, audio, device)

            # 清理对齐模型资源（可选）
            # del model_a
            # gc.collect()
            # torch.cuda.empty_cache()

            # 第三步：使用 Diarization 模型分配说话人标签
            diarize_model = whisperx.diarize.DiarizationPipeline(use_auth_token=hf_token, device=device)
            diarize_segments = diarize_model(audio)
            result = whisperx.assign_word_speakers(diarize_segments, result)

            # 输出最终包含说话人标签的结果
            print(result["segments"])  # segments 现在包含 speaker ID

            # 存储当前音频的识别结果
            results.append({
                "audio_file": audio_file,
                "result": result["segments"]
            })

        except Exception as e:
            # 捕获异常并记录错误信息
            results.append({
                "audio_file": audio_file,
                "error": str(e)
            })

    return results
