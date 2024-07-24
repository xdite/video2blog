import streamlit as st
import os
from downloader import download_video, get_subtitles, save_subtitles_as_srt, sanitize_filename, translate_subtitles, save_translated_subtitles

def main():
    st.title("YouTube 影片和字幕下载器")

    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 设置默认 URL
    if 'default_url' not in st.session_state:
        st.session_state.default_url = "https://www.youtube.com/watch?v=-X0jBz5_gCc"

    url = st.text_input("请输入 YouTube 影片 URL", value=st.session_state.default_url)

    if url != st.session_state.default_url:
        st.session_state.default_url = url

    # DeepL API Key 输入
    deepl_api_key = st.text_input("请输入 DeepL API Key", type="password")

    if st.button("下载"):
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
                safe_title = sanitize_filename(video_title)
                mp4_path = os.path.join(output_dir, f"{safe_title}.{video_ext}")
                status_text.text("影片下载成功!")

                # 创建下载链接
                with open(mp4_path, "rb") as file:
                    btn = st.download_button(
                        label="下载 MP4 文件",
                        data=file,
                        file_name=f"{safe_title}.{video_ext}",
                        mime="video/mp4"
                    )
            except Exception as e:
                st.error(f"影片下载失败: {str(e)}")

            # 获取并保存字幕
            try:
                subtitles = get_subtitles(video_id)
                if subtitles:
                    srt_path = os.path.join(output_dir, f"{safe_title}.srt")
                    save_subtitles_as_srt(subtitles, srt_path)
                    st.success("字幕获取并转换成功!")

                    # 创建字幕下载链接
                    with open(srt_path, "rb") as file:
                        btn = st.download_button(
                            label="下载 SRT 字幕文件",
                            data=file,
                            file_name=f"{safe_title}.srt",
                            mime="text/srt"
                        )

                    # 添加翻译按钮
                    if st.button("翻译字幕为简体中文"):
                        if deepl_api_key:
                            try:
                                translated_subtitles = translate_subtitles(subtitles, 'zh', deepl_api_key)
                                translated_srt_path = save_translated_subtitles(srt_path, translated_subtitles)
                                st.success("字幕翻译成功!")

                                # 创建翻译后的字幕下载链接
                                with open(translated_srt_path, "rb") as file:
                                    btn = st.download_button(
                                        label="下载翻译后的简体中文 SRT 字幕文件",
                                        data=file,
                                        file_name=f"{safe_title}.zh.srt",
                                        mime="text/srt"
                                    )
                            except Exception as e:
                                st.error(f"字幕翻译失败: {str(e)}")
                        else:
                            st.error("请输入有效的 DeepL API Key")
            except Exception as e:
                st.error(str(e))
        else:
            st.warning("请输入有效的 YouTube URL")

if __name__ == "__main__":
    main()
