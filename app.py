import streamlit as st
import os
from dotenv import load_dotenv
from downloader import download_video, get_subtitles, save_subtitles_as_srt, sanitize_filename
from translator import translate_srt_file
from video_to_pdf import video_to_pdf

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
    if 'zh_srt_path' not in st.session_state:
        st.session_state.zh_srt_path = None
    if 'safe_title' not in st.session_state:
        st.session_state.safe_title = None

    url = st.text_input("请输入 YouTube 影片 URL", value=st.session_state.default_url)

    if st.button("下载视频和字幕"):
        if url:
            with st.spinner("正在下载视频和字幕..."):
                try:
                    video_id = url.split("v=")[1]
                    video_title, video_ext = download_video(url, output_dir, lambda p: None)
                    st.session_state.safe_title = sanitize_filename(video_title)
                    st.session_state.mp4_path = os.path.join(output_dir, f"{st.session_state.safe_title}.{video_ext}")

                    subtitles = get_subtitles(video_id)
                    st.session_state.srt_path = os.path.join(output_dir, f"{st.session_state.safe_title}.srt")
                    save_subtitles_as_srt(subtitles, st.session_state.srt_path)

                    # 检查是否已存在中文字幕文件
                    st.session_state.zh_srt_path = os.path.join(output_dir, f"{st.session_state.safe_title}.zh.srt")
                    if os.path.exists(st.session_state.zh_srt_path):
                        st.success("视频、原始字幕和中文字幕下载成功！")
                    else:
                        st.success("视频和原始字幕下载成功！")
                except Exception as e:
                    st.error(f"下载失败: {str(e)}")
        else:
            st.warning("请输入有效的 YouTube URL")

    # 显示下载链接
    if st.session_state.mp4_path and os.path.exists(st.session_state.mp4_path):
        with open(st.session_state.mp4_path, "rb") as file:
            st.download_button(
                label="下载 MP4 文件",
                data=file,
                file_name=f"{st.session_state.safe_title}.mp4",
                mime="video/mp4"
            )

    if st.session_state.srt_path and os.path.exists(st.session_state.srt_path):
        with open(st.session_state.srt_path, "rb") as file:
            st.download_button(
                label="下载原始 SRT 字幕文件",
                data=file,
                file_name=f"{st.session_state.safe_title}.srt",
                mime="text/srt"
            )

    # 翻译字幕
    if st.session_state.srt_path and os.path.exists(st.session_state.srt_path):
        if not os.path.exists(st.session_state.zh_srt_path):
            if st.button("翻译字幕为简体中文"):
                with st.spinner("正在翻译字幕..."):
                    try:
                        deepl_api_key = os.getenv("DEEPL_API_KEY")
                        if not deepl_api_key:
                            st.error("未找到有效的 DeepL API Key。请检查 .env 文件。")
                        else:
                            st.session_state.zh_srt_path = translate_srt_file(
                                st.session_state.srt_path,
                                deepl_api_key,
                                progress_callback=lambda p: None
                            )
                            st.success("字幕翻译成功！")
                    except Exception as e:
                        st.error(f"翻译失败: {str(e)}")
        else:
            st.success("中文字幕文件已存在，无需翻译。")

    # 显示中文字幕下载链接
    if st.session_state.zh_srt_path and os.path.exists(st.session_state.zh_srt_path):
        with open(st.session_state.zh_srt_path, "rb") as file:
            st.download_button(
                label="下载中文 SRT 字幕文件",
                data=file,
                file_name=f"{st.session_state.safe_title}.zh.srt",
                mime="text/srt"
            )

    # 转换为 PDF
    if st.session_state.mp4_path and st.session_state.zh_srt_path and os.path.exists(st.session_state.zh_srt_path):
        if st.button("将视频转换为带中文字幕的 PDF"):
            png_progress_bar = st.progress(0)
            pdf_progress_bar = st.progress(0)
            status_text = st.empty()

            def update_png_progress(progress):
                png_progress_bar.progress(progress)
                status_text.text(f"生成字幕帧进度: {progress:.1%}")

            def update_pdf_progress(progress):
                pdf_progress_bar.progress(progress)
                status_text.text(f"转换 PDF 进度: {progress:.1%}")

            try:
                pdf_created, failed_frames = video_to_pdf(
                    st.session_state.mp4_path,
                    png_progress_callback=update_png_progress,
                    pdf_progress_callback=update_pdf_progress
                )

                pdf_path = f"{st.session_state.safe_title}.pdf"

                # 总是显示下载链接
                st.markdown(f"PDF 文件应该已经创建在以下路径：`{os.path.abspath(pdf_path)}`")
                st.download_button(
                    label="尝试下载 PDF 文件",
                    data=pdf_path,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf"
                )

                if os.path.exists(pdf_path):
                    st.success("系统检测到 PDF 文件已成功创建！")
                else:
                    st.warning("系统无法检测到 PDF 文件，但这可能是由于权限或路径问题。如果您确定文件已创建，可以尝试手动在上述路径查找。")

                if failed_frames:
                    st.info(f"注意：在处理过程中，第 {', '.join(map(str, failed_frames))} 帧出现问题被跳过。")

                if pdf_created:
                    st.success("PDF 创建过程完成，但请注意系统的文件检测结果。")
                else:
                    st.warning("PDF 创建过程可能遇到了一些问题，但文件可能仍然被成功创建。")

            except Exception as e:
                st.error(f"PDF 转换过程中发生错误: {str(e)}")

if __name__ == "__main__":
    main()
