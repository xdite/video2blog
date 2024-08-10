import os
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi
import re
import unicodedata

def sanitize_filename(filename):
    # 保留中文字符，只移除不允许的字符
    filename = re.sub(r'[\\/*?:"<>|]', "", filename)
    filename = filename.replace(' ', '_')
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
        'format': 'bestvideo[height<=1080][ext=mp4]',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': False,
        'progress_hooks': [yt_dlp_hook],
        'postprocessors': [],  # 移除所有后处理器，包括合并
    }

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info['formats']

        # 尝试找到 720p 或 1080p 的视频
        selected_format = None
        for f in formats:
            if f['ext'] == 'mp4' and f.get('height') in [720, 1080]:
                selected_format = f
                break

        if selected_format:
            ydl_opts['format'] = f"{selected_format['format_id']}+bestaudio[ext=m4a]/best[ext=mp4]/best"
        else:
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'

        # 下载视频
        info = ydl.extract_info(url, download=True)
        title = info['title']
        ext = info['ext']
        sanitized_title = sanitize_filename(title)
        file_path = os.path.join(output_dir, f"{sanitized_title}.{ext}")

        # 检查文件是否存在，如果不存在，尝试查找原始文件名
        if not os.path.exists(file_path):
            for filename in os.listdir(output_dir):
                if filename.endswith(f".{ext}") and title in filename:
                    file_path = os.path.join(output_dir, filename)
                    break

        return title, ext, file_path

def get_subtitles(video_id):
    try:
        # 首先尝试获取所有可用的字幕
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # 查找所有以 'en' 开头的语言代码
        en_transcripts = [t for t in transcript_list if t.language_code.startswith('en')]
        if en_transcripts:
            # 如果找到了英语字幕，使用第一个
            transcript = en_transcripts[0].fetch()
        else:
            # 如果没有找到英语字幕，尝试获取任何可用的字幕
            transcript = transcript_list.find_transcript(['en'])
        return transcript
    except Exception as e:
        # 如果出现异常，返回 None 而不是抛出异常
        print(f"无法获取字幕: {str(e)}")
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
