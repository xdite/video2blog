import os
import subprocess
import json
from PIL import Image
import shutil
from tqdm import tqdm

def get_video_dimensions(video_path):
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

def extract_frame(video_file, time, output_file):
    try:
        subprocess.check_call(['ffmpeg', '-ss', str(time), '-i', video_file, '-vframes', '1', '-q:v', '2', output_file, '-y'], stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to extract frame at time {time}")
        return False

def add_subtitle_to_image(image_file, subtitle_text, output_file, video_dimensions):
    frame_width, frame_height = video_dimensions
    font_size = int(frame_height / 20)
    y_position = int(frame_height * 0.9)

    try:
        ffmpeg_command = [
            'ffmpeg', '-i', image_file,
            '-vf', f"drawtext=fontfile=/System/Library/Fonts/PingFang.ttc:fontsize={font_size}:fontcolor=yellow:box=1:boxcolor=black@0.5:boxborderw=5:x=(w-tw)/2:y={y_position}:text='{subtitle_text}'",
            '-c:a', 'copy', output_file, '-y'
        ]
        subprocess.check_call(ffmpeg_command, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        print(f"Failed to add subtitle to image: {image_file}")
        return False

def parse_srt(srt_file):
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

def time_to_seconds(time_str):
    h, m, s = time_str.replace(',', '.').split(':')
    return int(h) * 3600 + int(m) * 60 + float(s)

def video_to_images(video_file_name: str):
    base_name = video_file_name.rsplit('.', 1)[0]
    zh_subtitle_file_name = base_name + '.zh.srt'

    subtitles = parse_srt(zh_subtitle_file_name)
    video_dimensions = get_video_dimensions(video_file_name)

    try:
        if not os.path.exists(base_name):
            os.makedirs(base_name)
    except OSError as e:
        print(f"Failed to create directory: {base_name}. Error: {e}")
        raise

    successful_frames = []

    for i, (start_time, end_time, text) in tqdm(enumerate(subtitles), total=len(subtitles), desc="Processing frames"):
        mid_time = (start_time + end_time) / 2
        frame_file = f"{base_name}/{i:04}_frame.png"
        subtitled_frame_file = f"{base_name}/{i:04}.png"

        if extract_frame(video_file_name, mid_time, frame_file):
            if add_subtitle_to_image(frame_file, text, subtitled_frame_file, video_dimensions):
                successful_frames.append(subtitled_frame_file)

            # Remove the intermediate frame file
            os.remove(frame_file)

    return successful_frames

def convert_png_to_pdf(input_files, output_filename):
    output_file = output_filename + '.pdf'

    images = []

    for filename in input_files:
        try:
            img = Image.open(filename)
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)
        except Exception as e:
            print(f"Error processing image {filename}: {e}")

    if images:
        images[0].save(output_file, "PDF", resolution=100.0, save_all=True, append_images=images[1:])
        print("Conversion from PNG to PDF is complete.")
    else:
        print("No valid images to convert to PDF.")

def video_to_pdf(video_file_name: str):
    base_name = video_file_name.rsplit('.', 1)[0]

    # Step 1: Convert video to images with subtitles
    successful_frames = video_to_images(video_file_name)

    # Step 2: Convert images to PDF
    if successful_frames:
        convert_png_to_pdf(successful_frames, base_name)
        print(f"Video has been converted to PDF: {base_name}.pdf")
    else:
        print("No frames were successfully processed. PDF creation failed.")

    # Clean up: remove individual frame images
    for frame in successful_frames:
        try:
            os.remove(frame)
        except OSError as e:
            print(f"Error deleting file {frame}: {e}")

    try:
        os.rmdir(base_name)
        print(f"Temporary directory {base_name} has been removed.")
    except OSError as e:
        print(f"Error removing directory {base_name}: {e}")
