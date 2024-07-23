import streamlit as st
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi

def download_video(url):
    ydl_opts = {'format': '18'}  # 使用 format 18 下載 mp4
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def get_subtitles(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        st.error(f"無法獲取字幕: {str(e)}")
        return None

def main():
    st.title("YouTube 影片和字幕下載器")

    url = st.text_input("請輸入 YouTube 影片 URL")

    if st.button("下載"):
        if url:
            video_id = url.split("v=")[1]

            # 下載影片
            try:
                download_video(url)
                st.success("影片下載成功!")
            except Exception as e:
                st.error(f"影片下載失敗: {str(e)}")

            # 獲取字幕
            subtitles = get_subtitles(video_id)
            if subtitles:
                st.success("字幕獲取成功!")
                st.text_area("字幕內容", value=str(subtitles), height=300)
        else:
            st.warning("請輸入有效的 YouTube URL")

if __name__ == "__main__":
    main()
