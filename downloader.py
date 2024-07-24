import os
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
import re
import unicodedata
import deepl

def sanitize_filename(filename):
    filename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore').decode()
    filename = filename.replace(' ', '_')
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = filename.lstrip('.')
    filename = re.sub(r'_{2,}', '_', filename)
    filename = filename[:255]
    if not filename:
        filename = "untitled"
    return filename

def download_video(url, output_dir, progress_callback):
    def yt_dlp_hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            if total_bytes:
                progress = downloaded_bytes / total_bytes
                progress_callback(progress)

    ydl_opts = {
        'format': '18',  # 使用 format 18 下载 mp4
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,  # 限制文件名为 ASCII 字符
        'progress_hooks': [yt_dlp_hook],
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info['title'], info['ext']

def get_subtitles(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return transcript
    except Exception as e:
        raise Exception(f"无法获取字幕: {str(e)}")

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

def translate_subtitles(subtitles, target_lang='zh', api_key=None):
    if not api_key:
        raise ValueError("DeepL API key is required for translation.")

    translator = deepl.Translator(api_key)
    translated_subtitles = []

    for subtitle in subtitles:
        translated_text = translator.translate_text(subtitle['text'], target_lang=target_lang)
        translated_subtitle = subtitle.copy()
        translated_subtitle['text'] = translated_text.text
        translated_subtitles.append(translated_subtitle)

    return translated_subtitles

def save_translated_subtitles(original_srt_path, translated_subtitles):
    filename, _ = os.path.splitext(original_srt_path)
    translated_srt_path = f"{filename}.zh.srt"
    save_subtitles_as_srt(translated_subtitles, translated_srt_path)
    return translated_srt_path
