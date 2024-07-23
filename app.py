import streamlit as st
import os
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
import re

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "", filename)

def download_video(url, output_path):
    ydl_opts = {
        'format': '18',  # 使用 format 18 下載 mp4
        'outtmpl': output_path
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info.get('title', 'video')

def get_subtitles(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        st.error(f"無法獲取字幕: {str(e)}")
        return None

def save_subtitles_as_srt(subtitles, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for i, subtitle in enumerate(subtitles, start=1):
            start = subtitle['start']
            duration = subtitle['duration']
            end = start + duration

            start_time = '{:02d}:{:02d}:{:02d},{:03d}'.format(
                int(start // 3600),
                int(start % 3600 // 60),
                int(start % 60),
                int(start % 1 * 1000)
            )
            end_time = '{:02d}:{:02d}:{:02d},{:03d}'.format(
                int(end // 3600),
                int(end % 3600 // 60),
                int(end % 60),
                int(end % 1 * 1000)
            )

            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{subtitle['text']}\n\n")

def main():
    st.title("YouTube 影片和字幕下載器")

    if not os.path.exists('data'):
        os.makedirs('data')

    url = st.text_input("請輸入 YouTube 影片 URL")

    if st.button("下載"):
        if url:
            video_id = url.split("v=")[1]

            # 下載影片
            try:
                video_title = download_video(url, 'data/%(title)s.%(ext)s')
                safe_title = sanitize_filename(video_title)
                mp4_path = f"data/{safe_title}.mp4"
                st.success("影片下載成功!")

                # 創建下載連結
                with open(mp4_path, "rb") as file:
                    btn = st.download_button(
                        label="下載 MP4 檔案",
                        data=file,
                        file_name=f"{safe_title}.mp4",
                        mime="video/mp4"
                    )
            except Exception as e:
                st.error(f"影片下載失敗: {str(e)}")

            # 獲取並保存字幕
            subtitles = get_subtitles(video_id)
            if subtitles:
                srt_path = f"data/{safe_title}.srt"
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
        else:
            st.warning("請輸入有效的 YouTube URL")

if __name__ == "__main__":
    main()
