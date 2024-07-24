import streamlit as st
import os
from dotenv import load_dotenv
from downloader import download_video, get_subtitles, save_subtitles_as_srt, sanitize_filename
from translator import translate_srt_file
from video_to_pdf import video_to_pdf

# 加载 .env 文件
load_dotenv()

def main():
    st.title("YouTube 影片下载器与字幕转换器")

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
    if 'translated_srt_path' not in st.session_state:
        st.session_state.translated_srt_path = None

    url = st.text_input("请输入 YouTube 影片 URL", value=st.session_state.default_url)

    if url != st.session_state.default_url:
        st.session_state.default_url = url

    download_button = st.empty()
    if download_button.button("下载视频和字幕"):
        if url:
            video_id = url.split("v=")[1]

            # 创建进度条
            progress_bar = st.progress(0)
            status_text = st.empty()

            # 下载影片
            try:
                def update_progress(progress):
                    progress_bar.progress(progress)
                    status_text.text(f"下载进度: {progress:.1%}")

                video_title, video_ext = download_video(url, output_dir, update_progress)
                st.session_state.safe_title = sanitize_filename(video_title)
                st.session_state.mp4_path = os.path.join(output_dir, f"{st.session_state.safe_title}.{video_ext}")
                status_text.text("影片下载成功!")
            except Exception as e:
                st.error(f"影片下载失败: {str(e)}")
                return

            # 获取并保存字幕
            try:
                subtitles = get_subtitles(video_id)
                if subtitles:
                    st.session_state.srt_path = os.path.join(output_dir, f"{st.session_state.safe_title}.srt")
                    save_subtitles_as_srt(subtitles, st.session_state.srt_path)
                    st.success("字幕获取并转换成功!")
            except Exception as e:
                st.error(f"字幕获取失败: {str(e)}")
        else:
            st.warning("请输入有效的 YouTube URL")

    # 显示下载链接
    if st.session_state.mp4_path:
        with open(st.session_state.mp4_path, "rb") as file:
            st.download_button(
                label="下载 MP4 文件",
                data=file,
                file_name=f"{st.session_state.safe_title}.mp4",
                mime="video/mp4"
            )

    if st.session_state.srt_path:
        with open(st.session_state.srt_path, "rb") as file:
            st.download_button(
                label="下载原始 SRT 字幕文件",
                data=file,
                file_name=f"{st.session_state.safe_title}.srt",
                mime="text/srt"
            )

        # 检查是否已存在中文字幕文件
        zh_srt_path = st.session_state.srt_path.replace('.srt', '.zh.srt')
        if os.path.exists(zh_srt_path):
            st.session_state.translated_srt_path = zh_srt_path
            st.success("已找到现有的中文字幕文件。")
        else:
            # 显示翻译选项
            translate_button = st.empty()
            if translate_button.button("翻译字幕为简体中文"):
                deepl_api_key = os.getenv("DEEPL_API_KEY")
                if not deepl_api_key:
                    st.error("未找到有效的 DeepL API Key。请检查 .env 文件。")
                else:
                    # 创建翻译进度条
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    try:
                        def update_translation_progress(progress):
                            progress_bar.progress(progress)
                            status_text.text(f"翻译进度: {progress:.1%}")

                        st.session_state.translated_srt_path = translate_srt_file(
                            st.session_state.srt_path,
                            deepl_api_key,
                            progress_callback=update_translation_progress
                        )
                        status_text.text("字幕翻译成功!")
                    except Exception as e:
                        st.error(f"字幕翻译失败: {str(e)}")

    # 显示翻译后的字幕下载链接
    if st.session_state.translated_srt_path:
        with open(st.session_state.translated_srt_path, "rb") as file:
            st.download_button(
                label="下载简体中文 SRT 字幕文件",
                data=file,
                file_name=f"{st.session_state.safe_title}.zh.srt",
                mime="text/srt"
            )

        # 添加转换为 PDF 的选项
        if st.button("将视频转换为带中文字幕的 PDF"):
            try:
                with st.spinner("正在转换视频为 PDF，这可能需要一些时间..."):
                    video_to_pdf(st.session_state.mp4_path)
                st.success(f"转换完成！PDF 文件已保存为 {st.session_state.safe_title}.pdf")

                # 提供 PDF 下载链接
                pdf_path = f"{st.session_state.safe_title}.pdf"
                with open(pdf_path, "rb") as file:
                    st.download_button(
                        label="下载带中文字幕的 PDF",
                        data=file,
                        file_name=pdf_path,
                        mime="application/pdf"
                    )
            except Exception as e:
                st.error(f"PDF 转换失败: {str(e)}")

if __name__ == "__main__":
    main()
