import streamlit as st
import os
import whisper
import torch
from moviepy.editor import VideoFileClip
import numpy as np
from dotenv import load_dotenv
from downloader import download_video, get_subtitles, sanitize_filename

load_dotenv()

def extract_audio(video_path):
    video = VideoFileClip(video_path)
    audio = video.audio
    audio_path = "temp_audio.wav"
    audio.write_audiofile(audio_path, fps=16000, nbytes=2, codec='pcm_s16le')
    return audio_path

def detect_language(audio_file, model):
    audio = whisper.load_audio(audio_file)
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    _, probs = model.detect_language(mel)
    return max(probs, key=probs.get)

def format_timecode(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

def process_audio(audio_file, model, detected_language, frame_duration=30, debug=False, progress_callback=None):
    audio = whisper.load_audio(audio_file)
    audio_duration = len(audio) / 16000  # 假设采样率为16000

    srt_output = []
    total_segments = len(range(0, len(audio), 16000 * frame_duration))

    for i, start in enumerate(range(0, len(audio), 16000 * frame_duration), 1):
        end = min(start + 16000 * frame_duration, len(audio))
        audio_segment = audio[start:end]

        result = model.transcribe(audio_segment, language=detected_language)

        if result['text'].strip():
            start_time = start / 16000
            end_time = end / 16000

            srt_entry = (
                f"{i}\n"
                f"{format_timecode(start_time)} --> {format_timecode(end_time)}\n"
                f"{result['text'].strip()}\n\n"
            )
            srt_output.append(srt_entry)

            if debug:
                st.text(f"处理完成段落 {i}: {format_timecode(start_time)} --> {format_timecode(end_time)}")
                st.text(f"文本: {result['text'].strip()}\n")

        if progress_callback:
            progress_callback(i / total_segments)

    return srt_output

def generate_subtitles_with_whisper(video_filename, model_name="base", frame_duration=30, debug=False):
    output_srt = video_filename.rsplit('.', 1)[0] + '.srt'

    # 创建进度条
    progress_bar = st.progress(0)
    status_text = st.empty()

    # 自定义回调函数来更新进度
    def progress_callback(progress):
        progress_bar.progress(progress)
        status_text.text(f"正在处理音频... {progress:.1%}")

    try:
        # 加载模型
        status_text.text("正在加载 Whisper 模型...")
        model = whisper.load_model(model_name)

        # 提取音频
        status_text.text("正在提取音频...")
        audio_file = extract_audio(video_filename)

        # 检测语言
        status_text.text("正在检测语言...")
        detected_language = detect_language(audio_file, model)
        st.write(f"检测到的语言: {detected_language}")

        # 处理音频
        status_text.text("正在转录音频...")
        srt_output = process_audio(audio_file, model, detected_language, frame_duration, debug, progress_callback)

        # 保存为 SRT 格式
        status_text.text("正在保存字幕...")
        with open(output_srt, "w", encoding="utf-8") as srt_file:
            srt_file.writelines(srt_output)

        # 删除临时音频文件
        os.remove(audio_file)

        status_text.text("字幕生成完成！")
        progress_bar.progress(1.0)

        return output_srt
    except Exception as e:
        raise Exception(f"Whisper 处理失败: {str(e)}")

def main():
    st.title("YouTube 视频字幕生成器")

    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 初始化 session state
    if 'default_url' not in st.session_state:
        st.session_state.default_url = "https://www.youtube.com/watch?v=-X0jBz5_gCc"
    if 'mp4_path' not in st.session_state:
        st.session_state.mp4_path = None
    if 'srt_path' not in st.session_state:
        st.session_state.srt_path = None
    if 'safe_title' not in st.session_state:
        st.session_state.safe_title = None

    url = st.text_input("请输入 YouTube 视频 URL", value=st.session_state.default_url)
    frame_duration = st.slider("选择音频片段长度（秒）", min_value=10, max_value=60, value=30, step=5)
    debug = st.checkbox("显示调试信息")

    if st.button("获取字幕"):
        if url:
            with st.spinner("正在处理视频..."):
                try:
                    # 添加下载进度条
                    download_progress = st.progress(0)
                    download_status = st.empty()

                    def update_download_progress(progress):
                        download_progress.progress(progress)
                        download_status.text(f"下载进度: {progress:.1%}")

                    video_title, video_ext, mp4_path = download_video(url, output_dir, update_download_progress)
                    st.session_state.safe_title = sanitize_filename(video_title)
                    st.session_state.mp4_path = mp4_path

                    download_status.text("正在获取字幕...")
                    subtitles = get_subtitles(url.split("v=")[1])

                    if subtitles:
                        st.success("成功获取 YouTube 字幕！")
                        st.session_state.srt_path = os.path.join(output_dir, f"{st.session_state.safe_title}.srt")
                        with open(st.session_state.srt_path, 'w', encoding='utf-8') as f:
                            f.writelines(subtitles)
                    else:
                        st.warning("无法获取 YouTube 字幕，正在使用 Whisper 生成字幕...")
                        st.session_state.srt_path = generate_subtitles_with_whisper(st.session_state.mp4_path, frame_duration=frame_duration, debug=debug)
                        st.success("使用 Whisper 成功生成字幕！")

                    # 清除进度条和状态文本
                    download_progress.empty()
                    download_status.empty()

                except Exception as e:
                    st.error(f"处理失败: {str(e)}")
        else:
            st.warning("请输入有效的 YouTube URL")

    # 显示下载链接
    if st.session_state.srt_path and os.path.exists(st.session_state.srt_path):
        with open(st.session_state.srt_path, "rb") as file:
            st.download_button(
                label="下载 SRT 字幕文件",
                data=file,
                file_name=f"{st.session_state.safe_title}.srt",
                mime="text/srt"
            )

if __name__ == "__main__":
    main()
