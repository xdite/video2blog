import wave
import contextlib
import sys
import whisper
import numpy as np
import os
from moviepy.editor import VideoFileClip

def extract_audio(video_path):
    video = VideoFileClip(video_path)
    audio = video.audio
    audio_path = "temp_audio.wav"
    audio.write_audiofile(audio_path, fps=16000, nbytes=2, codec='pcm_s16le')
    return audio_path

def detect_language(audio_file, model):
    audio = whisper.load_audio(audio_file)
    audio = whisper.pad_or_trim(audio)
    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    _, probs = model.detect_language(mel)
    return max(probs, key=probs.get)

def format_timecode(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

def process_audio(audio_file, model, detected_language, frame_duration=30, debug=False):
    audio = whisper.load_audio(audio_file)
    audio_duration = len(audio) / 16000  # 假设采样率为16000

    srt_output = []
    for i, start in enumerate(range(0, len(audio), 16000 * frame_duration), 1):
        end = min(start + 16000 * frame_duration, len(audio))
        audio_segment = audio[start:end]

        result = model.transcribe(audio_segment, language=detected_language)

        if result['text'].strip():
            start_time = start / 16000
            end_time = end / 16000

            srt_entry = (
                f"{i}\n"
                f"{format_timecode(start_time)} --> {format_timecode(end_time)}\n"
                f"{result['text'].strip()}\n\n"
            )
            srt_output.append(srt_entry)

            if debug:
                print(f"处理完成段落 {i}: {format_timecode(start_time)} --> {format_timecode(end_time)}")
                print(f"文本: {result['text'].strip()}\n")

    return srt_output

def main(video_file, frame_duration=30, debug=False):
    model = whisper.load_model("base")

    audio_file = extract_audio(video_file)

    detected_language = detect_language(audio_file, model)
    print(f"检测到的语言: {detected_language}")

    srt_output = process_audio(audio_file, model, detected_language, frame_duration, debug)

    os.remove(audio_file)

    output_srt = os.path.splitext(video_file)[0] + ".srt"
    with open(output_srt, 'w', encoding='utf-8') as f:
        f.writelines(srt_output)

    print(f"SRT 文件已生成: {output_srt}")

if __name__ == '__main__':
    video_file = sys.argv[1]
    frame_duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    debug = len(sys.argv) > 3 and sys.argv[3].lower() == 'debug'
    main(video_file, frame_duration, debug)
