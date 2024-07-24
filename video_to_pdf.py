import os
import subprocess
import json
from PIL import Image
from tqdm import tqdm

def get_video_dimensions(video_path):
    try:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=width,height,sample_aspect_ratio", "-of", "json", video_path]
        output = subprocess.check_output(cmd).decode("utf-8")
        dimensions = json.loads(output)["streams"][0]

        width = dimensions["width"]
        height = dimensions["height"]
        sar = dimensions.get("sample_aspect_ratio", "1:1").split(":")
        sar = float(sar[0]) / float(sar[1])

        display_width = int(width * sar)

        return display_width, height
    except Exception:
        return 1920, 1080  # 返回默认值，以防获取尺寸失败

def process_frame(video_file, time, subtitle_text, output_file, video_dimensions):
    frame_width, frame_height = video_dimensions
    font_size = int(frame_height / 20)
    y_position = int(frame_height * 0.9)

    try:
        ffmpeg_command = [
            'ffmpeg', '-ss', str(time),
            '-i', video_file,
            '-vf', f"drawtext=fontfile=/System/Library/Fonts/PingFang.ttc:fontsize={font_size}:fontcolor=yellow:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-tw)/2:y={y_position}:text='{subtitle_text}'",
            '-vframes', '1',
            '-q:v', '2',
            output_file,
            '-y'
        ]
        subprocess.check_call(ffmpeg_command, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def parse_srt(srt_file):
    try:
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read()

        subtitles = []
        for block in content.strip().split('\n\n'):
            parts = block.split('\n')
            if len(parts) >= 3:
                time_str = parts[1]
                text = ' '.join(parts[2:])
                start_time, end_time = time_str.split(' --> ')
                start_time = time_to_seconds(start_time)
                end_time = time_to_seconds(end_time)
                subtitles.append((start_time, end_time, text))

        return subtitles
    except Exception:
        return []  # 如果解析失败，返回空列表

def time_to_seconds(time_str):
    try:
        h, m, s = time_str.replace(',', '.').split(':')
        return int(h) * 3600 + int(m) * 60 + float(s)
    except Exception:
        return 0  # 如果转换失败，返回0

def video_to_images(video_file_name: str, progress_callback=None):
    base_name = video_file_name.rsplit('.', 1)[0]
    zh_subtitle_file_name = base_name + '.zh.srt'

    subtitles = parse_srt(zh_subtitle_file_name)
    video_dimensions = get_video_dimensions(video_file_name)

    try:
        if not os.path.exists(base_name):
            os.makedirs(base_name)
    except Exception:
        pass

    successful_frames = []
    failed_frames = []

    for i, (start_time, end_time, text) in enumerate(subtitles):
        mid_time = (start_time + end_time) / 2
        output_file = f"{base_name}/{i:04}.png"

        if process_frame(video_file_name, mid_time, text, output_file, video_dimensions):
            successful_frames.append(output_file)
        else:
            failed_frames.append(i)

        if progress_callback:
            progress_callback((i + 1) / len(subtitles))

    return successful_frames, failed_frames

def convert_png_to_pdf(input_files, output_filename, progress_callback=None):
    output_file = output_filename + '.pdf'

    images = []

    for i, filename in enumerate(input_files):
        try:
            img = Image.open(filename)
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)
        except Exception:
            continue

        if progress_callback:
            progress_callback((i + 1) / len(input_files))

    if images:
        try:
            images[0].save(output_file, "PDF", resolution=100.0, save_all=True, append_images=images[1:])
            return True
        except Exception:
            return False
    else:
        return False

def video_to_pdf(video_file_name: str, png_progress_callback=None, pdf_progress_callback=None):
    base_name = video_file_name.rsplit('.', 1)[0]

    # Step 1: Convert video to images with subtitles
    successful_frames, failed_frames = video_to_images(video_file_name, png_progress_callback)

    # Step 2: Convert images to PDF
    pdf_created = False
    if successful_frames:
        pdf_created = convert_png_to_pdf(successful_frames, base_name, pdf_progress_callback)

    # Clean up: remove individual frame images
    for frame in successful_frames:
        try:
            os.remove(frame)
        except Exception:
            pass

    try:
        os.rmdir(base_name)
    except Exception:
        pass

    return pdf_created, failed_frames
