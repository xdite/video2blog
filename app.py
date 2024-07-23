import streamlit as st
import os
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
import re
import unicodedata

def sanitize_filename(filename):
    # 將檔案名轉換為 ASCII 字符，移除非 ASCII 字符
    filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()

    # 將空格替換為下劃線
    filename = filename.replace(' ', '_')

    # 移除或替換不允許的字符
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)

    # 移除開頭的點號（在某些系統中可能會隱藏檔案）
    filename = filename.lstrip('.')

    # 將多個連續的下劃線替換為單個下劃線
    filename = re.sub(r'_{2,}', '_', filename)

    # 限制檔案名長度（例如，最長 255 字符）
    filename = filename[:255]

    # 確保檔案名不為空
    if not filename:
        filename = "untitled"

    return filename

def download_video(url, output_dir):
    ydl_opts = {
        'format': '18',  # 使用 format 18 下載 mp4
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,  # 限制文件名為 ASCII 字符
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info['title'], info['ext']

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

    output_dir = 'data'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    url = st.text_input("請輸入 YouTube 影片 URL")

    if st.button("下載"):
        if url:
            video_id = url.split("v=")[1]

            # 下載影片
            try:
                video_title, video_ext = download_video(url, output_dir)
                safe_title = sanitize_filename(video_title)
                mp4_path = os.path.join(output_dir, f"{safe_title}.{video_ext}")
                st.success("影片下載成功!")

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
        else:
            st.warning("請輸入有效的 YouTube URL")

if __name__ == "__main__":
    main()
