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

    if 'default_url' not in st.session_state:
        st.session_state.default_url = "https://www.youtube.com/watch?v=-X0jBz5_gCc"

    url = st.text_input("请输入 YouTube 影片 URL", value=st.session_state.default_url)

    if st.button("处理视频"):
        if url:
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # 下载视频
                status_text.text("正在下载视频...")
                video_title, video_ext = download_video(url, output_dir, lambda p: progress_bar.progress(p * 0.4))
                safe_title = sanitize_filename(video_title)
                mp4_path = os.path.join(output_dir, f"{safe_title}.{video_ext}")

                # 获取字幕
                status_text.text("正在获取字幕...")
                progress_bar.progress(0.4)
                video_id = url.split("v=")[1]
                subtitles = get_subtitles(video_id)
                srt_path = os.path.join(output_dir, f"{safe_title}.srt")
                save_subtitles_as_srt(subtitles, srt_path)
                progress_bar.progress(0.5)

                # 检查或翻译字幕
                zh_srt_path = srt_path.replace('.srt', '.zh.srt')
                if not os.path.exists(zh_srt_path):
                    status_text.text("正在翻译字幕...")
                    deepl_api_key = os.getenv("DEEPL_API_KEY")
                    zh_srt_path = translate_srt_file(
                        srt_path,
                        deepl_api_key,
                        progress_callback=lambda p: progress_bar.progress(0.5 + p * 0.3)
                    )
                else:
                    progress_bar.progress(0.8)

                # 转换为 PDF
                status_text.text("正在转换为 PDF...")
                video_to_pdf(mp4_path)
                progress_bar.progress(1.0)
                status_text.text("处理完成！")

                # 显示下载链接
                st.download_button("下载 MP4 文件", open(mp4_path, "rb"), f"{safe_title}.mp4", "video/mp4")
                st.download_button("下载原始 SRT 字幕文件", open(srt_path, "rb"), f"{safe_title}.srt", "text/srt")
                st.download_button("下载中文 SRT 字幕文件", open(zh_srt_path, "rb"), f"{safe_title}.zh.srt", "text/srt")
                pdf_path = f"{safe_title}.pdf"
                st.download_button("下载带中文字幕的 PDF", open(pdf_path, "rb"), pdf_path, "application/pdf")

            except Exception as e:
                st.error(f"处理失败: {str(e)}")
        else:
            st.warning("请输入有效的 YouTube URL")

if __name__ == "__main__":
    main()
