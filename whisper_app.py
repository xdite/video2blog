import streamlit as st
import os
from dotenv import load_dotenv
from downloader import download_video, get_subtitles, save_subtitles_as_srt, sanitize_filename
import whisper
import subprocess
import json
import multiprocessing

load_dotenv()

def generate_subtitles_with_whisper_ctranslate2(video_filename, model="medium"):
    num_cores = multiprocessing.cpu_count()
    st.write(f"使用 {num_cores} 个 CPU 核心进行处理")

    output_srt = video_filename.rsplit('.', 1)[0] + '.srt'

    command = [
        "whisper-ctranslate2",
        "--model", model,
        "--threads", str(num_cores),
        "--output_format", "srt",
        video_filename
    ]

    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        return output_srt
    except subprocess.CalledProcessError as e:
        raise Exception(f"Whisper-ctranslate2 处理失败: {e.stderr}")

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
                        st.warning("无法获取 YouTube 字幕，正在使用 Whisper-ctranslate2 生成字幕...")
                        with st.spinner("正在使用 Whisper-ctranslate2 生成字幕，这可能需要几分钟..."):
                            st.session_state.srt_path = generate_subtitles_with_whisper_ctranslate2(st.session_state.mp4_path)
                        st.success("使用 Whisper-ctranslate2 成功生成字幕！")

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
