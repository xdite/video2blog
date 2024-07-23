import streamlit as st
import os
from downloader import download_video, get_subtitles, save_subtitles_as_srt, sanitize_filename

def main():
    st.title("YouTube 影片和字幕下載器")

    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 設置默認 URL
    if 'default_url' not in st.session_state:
        st.session_state.default_url = "https://www.youtube.com/watch?v=-X0jBz5_gCc"

    url = st.text_input("請輸入 YouTube 影片 URL", value=st.session_state.default_url)

    if url != st.session_state.default_url:
        st.session_state.default_url = url

    if st.button("下載"):
        if url:
            video_id = url.split("v=")[1]

            # 創建進度條
            progress_bar = st.progress(0)
            status_text = st.empty()

            # 下載影片
            try:
                def update_progress(progress):
                    progress_bar.progress(progress)
                    status_text.text(f"下載進度: {progress:.1%}")

                video_title, video_ext = download_video(url, output_dir, update_progress)
                safe_title = sanitize_filename(video_title)
                mp4_path = os.path.join(output_dir, f"{safe_title}.{video_ext}")
                status_text.text("影片下載成功!")

                # 創建下載連結
                with open(mp4_path, "rb") as file:
                    btn = st.download_button(
                        label="下載 MP4 檔案",
                        data=file,
                        file_name=f"{safe_title}.{video_ext}",
                        mime="video/mp4"
                    )
            except Exception as e:
                st.error(f"影片下載失敗: {str(e)}")

            # 獲取並保存字幕
            try:
                subtitles = get_subtitles(video_id)
                if subtitles:
                    srt_path = os.path.join(output_dir, f"{safe_title}.srt")
                    save_subtitles_as_srt(subtitles, srt_path)
                    st.success("字幕獲取並轉換成功!")

                    # 創建字幕下載連結
                    with open(srt_path, "rb") as file:
                        btn = st.download_button(
                            label="下載 SRT 字幕檔案",
                            data=file,
                            file_name=f"{safe_title}.srt",
                            mime="text/srt"
                        )
            except Exception as e:
                st.error(str(e))
        else:
            st.warning("請輸入有效的 YouTube URL")

if __name__ == "__main__":
    main()
