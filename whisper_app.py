import streamlit as st
import os
from dotenv import load_dotenv
from downloader import download_video, get_subtitles, save_subtitles_as_srt, sanitize_filename
import whisper

load_dotenv()

def generate_subtitles_with_whisper(audio_file):
    model = whisper.load_model("base")
    result = model.transcribe(audio_file)

    subtitles = []
    for segment in result["segments"]:
        subtitles.append({
            'start': segment['start'],
            'duration': segment['end'] - segment['start'],
            'text': segment['text']
        })

    return subtitles

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

                    video_title, video_ext = download_video(url, output_dir, update_download_progress)
                    st.session_state.safe_title = sanitize_filename(video_title)
                    st.session_state.mp4_path = os.path.join(output_dir, f"{st.session_state.safe_title}.{video_ext}")

                    download_status.text("正在获取字幕...")
                    subtitles = get_subtitles(url.split("v=")[1])

                    if subtitles:
                        st.success("成功获取 YouTube 字幕！")
                    else:
                        st.warning("无法获取 YouTube 字幕，正在使用 Whisper 生成字幕...")
                        with st.spinner("正在加载 Whisper 模型并生成字幕，这可能需要几分钟..."):
                            subtitles = generate_subtitles_with_whisper(st.session_state.mp4_path)
                        st.success("使用 Whisper 成功生成字幕！")

                    st.session_state.srt_path = os.path.join(output_dir, f"{st.session_state.safe_title}.srt")
                    save_subtitles_as_srt(subtitles, st.session_state.srt_path)

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
