import os
from moviepy.editor import TextClip, ImageClip, CompositeVideoClip, VideoFileClip
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import subprocess
import json
from PIL import Image
import shutil

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

def process_subtitle(args):
    i, zh_subtitle, video_file_name, base_name = args

    clip = VideoFileClip(video_file_name)

    zh_parts = zh_subtitle.split("\n")

    if len(zh_parts) >= 3:
        times = zh_parts[1].split(" --> ")
        start_time = times[0].split(":")
        end_time = times[1].split(":")
        start_time = int(start_time[0])*3600 + int(start_time[1])*60 + float(start_time[2].replace(",", "."))
        end_time = int(end_time[0])*3600 + int(end_time[1])*60 + float(end_time[2].replace(",", "."))

        mid_time = start_time + ((end_time - start_time) / 3)

        zh_text = " ".join(zh_parts[2:])
        frame_width, frame_height = get_video_dimensions(video_file_name)

        if frame_width > frame_height:
            scale_factor = frame_width / 1920
        else:
            scale_factor = frame_height / 1920

        zh_text_size = 50 * scale_factor

        if frame_width > 640:
            zh_text_pos = ('center', frame_height - 100)
        else:
            zh_text_pos = ('center', frame_height - 30)

        if os.sys.platform == "darwin":
            font_name = "黑體-簡-中黑"
        else:
            font_name = "Noto-Sans-Mono-CJK-SC"

        zh_text_clip = (TextClip(zh_text, font=font_name, fontsize=zh_text_size, bg_color='black', color='yellow', stroke_width=0.25*scale_factor)
            .set_duration(end_time - mid_time)
            .set_position(zh_text_pos))

        frame = clip.get_frame(mid_time)
        frame_clip = ImageClip(frame).set_duration(end_time - mid_time).resize((frame_width, frame_height))

        final = CompositeVideoClip([frame_clip, zh_text_clip])
        final.save_frame(f"{base_name}/{i:04}.png")

    return i

def video_to_images(video_file_name: str):
    base_name = video_file_name.rsplit('.', 1)[0]
    zh_subtitle_file_name = base_name + '.zh.srt'

    with open(zh_subtitle_file_name, "r") as f:
        zh_subtitles = f.read().split("\n\n")

    try:
        if not os.path.exists(base_name):
            os.makedirs(base_name)
    except OSError as e:
        print(f"Failed to create directory: {base_name}. Error: {e}")
        raise

    with Pool(cpu_count()) as pool:
        for _ in tqdm(pool.imap_unordered(process_subtitle, [(i, zh_subtitles[i], video_file_name, base_name) for i in range(len(zh_subtitles))]), total=len(zh_subtitles)):
            pass

def convert_png_to_pdf(input_directory, output_filename):
    output_file = output_filename + '.pdf'

    images = []

    for filename in sorted(os.listdir(input_directory)):
        if filename.endswith(".png"):
            img = Image.open(os.path.join(input_directory, filename))
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)

    if images:
        images[0].save(output_file, "PDF", resolution=100.0, save_all=True, append_images=images[1:])

    print("Conversion from PNG to PDF is complete.")

    try:
        shutil.rmtree(input_directory)
        print("Directory deleted successfully.")
    except OSError as e:
        print("Error: %s : %s" % (input_directory, e.strerror))

def video_to_pdf(video_file_name: str):
    base_name = video_file_name.rsplit('.', 1)[0]

    # Step 1: Convert video to images with subtitles
    video_to_images(video_file_name)

    # Step 2: Convert images to PDF
    convert_png_to_pdf(base_name, base_name)

    print(f"Video has been converted to PDF: {base_name}.pdf")
