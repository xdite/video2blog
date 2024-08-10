import os
from yt_dlp import YoutubeDL
from youtube_transcript_api import YouTubeTranscriptApi

def download_video(url, output_dir, progress_callback):
    def yt_dlp_hook(d):
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes')
            downloaded_bytes = d.get('downloaded_bytes', 0)
            if total_bytes:
                progress = downloaded_bytes / total_bytes
                progress_callback(progress)
        elif d['status'] == 'finished':
            global downloaded_file_path
            downloaded_file_path = d['filename']

    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]',
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'restrictfilenames': True,
        'progress_hooks': [yt_dlp_hook],
        'postprocessors': [],
    }

    global downloaded_file_path
    downloaded_file_path = None

    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

        if downloaded_file_path and os.path.exists(downloaded_file_path):
            return os.path.basename(downloaded_file_path), downloaded_file_path
        else:
            raise FileNotFoundError(f"无法找到下载的视频文件")

def get_subtitles(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        en_transcripts = [t for t in transcript_list if t.language_code.startswith('en')]
        if en_transcripts:
            transcript = en_transcripts[0].fetch()
        else:
            transcript = transcript_list.find_transcript(['en'])
        return transcript
    except Exception as e:
        print(f"无法获取字幕: {str(e)}")
        return None

def save_subtitles_as_srt(subtitles, filename):
    with open(filename, 'w', encoding='utf-8') as f:
        for i, subtitle in enumerate(subtitles, start=1):
            start = subtitle['start']
            duration = subtitle['duration']
            end = start + duration
            start_time = '{:02d}:{:02d}:{:02d},{:03d}'.format(
                int(start // 3600), int(start % 3600 // 60),
                int(start % 60), int(start % 1 * 1000)
            )
            end_time = '{:02d}:{:02d}:{:02d},{:03d}'.format(
                int(end // 3600), int(end % 3600 // 60),
                int(end % 60), int(end % 1 * 1000)
            )
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{subtitle['text']}\n\n")
