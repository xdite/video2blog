import webrtcvad
import wave
import contextlib
import collections
import sys
import whisper
import numpy as np
import os
from moviepy.editor import VideoFileClip
import datetime

def extract_audio(video_path):
    video = VideoFileClip(video_path)
    audio = video.audio
    audio_path = "temp_audio.wav"
    audio.write_audiofile(audio_path, fps=16000, nbytes=2, codec='pcm_s16le')

    with wave.open(audio_path, 'rb') as wf:
        nchannels, sampwidth, framerate, nframes, comptype, compname = wf.getparams()
        frames = wf.readframes(nframes)

    frames = np.frombuffer(frames, dtype=np.int16)
    if nchannels == 2:
        frames = frames.reshape(-1, 2)
        frames = frames.mean(axis=1).astype(np.int16)

    with wave.open(audio_path, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(frames.tobytes())

    return audio_path

def read_wave(path):
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())

        if num_channels == 2:
            pcm_data = np.frombuffer(pcm_data, dtype=np.int16)
            pcm_data = pcm_data.reshape(-1, 2).mean(axis=1).astype(np.int16)
            pcm_data = pcm_data.tobytes()

        return pcm_data, sample_rate

def frame_generator(frame_duration_ms, audio, sample_rate):
    n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
    offset = 0
    while offset + n < len(audio):
        yield audio[offset:offset + n]
        offset += n

def vad_collector(sample_rate, frame_duration_ms, padding_duration_ms, vad, frames):
    num_padding_frames = int(padding_duration_ms / frame_duration_ms)
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False
    voiced_frames = []
    for frame in frames:
        is_speech = vad.is_speech(frame, sample_rate)
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                for f, s in ring_buffer:
                    voiced_frames.append(f)
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                triggered = False
                yield b''.join(voiced_frames)
                ring_buffer.clear()
                voiced_frames = []
    if voiced_frames:
        yield b''.join(voiced_frames)

def write_wave(path, audio, sample_rate):
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)

def detect_language(audio_file, model):
    # 使用較短的音頻片段來檢測語言，以加快速度
    audio = whisper.load_audio(audio_file)
    audio = whisper.pad_or_trim(audio)

    mel = whisper.log_mel_spectrogram(audio).to(model.device)
    _, probs = model.detect_language(mel)

    detected_language = max(probs, key=probs.get)
    print(f"檢測到的語言: {detected_language}")
    return detected_language

def format_timecode(seconds):
    """將秒數轉換為 SRT 格式的時間碼"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = seconds % 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{int(seconds):02d},{milliseconds:03d}"

def main(video_file, debug=False):
    model = whisper.load_model("base")

    audio_file = extract_audio(video_file)

    detected_language = detect_language(audio_file, model)
    print(f"檢測到的語言: {detected_language}")

    audio, sample_rate = read_wave(audio_file)

    vad = webrtcvad.Vad(3)

    frames = frame_generator(30, audio, sample_rate)
    segments = vad_collector(sample_rate, 30, 300, vad, frames)

    srt_output = []
    segment_count = 0
    total_duration = 0

    for i, segment in enumerate(segments):
        path = f'chunk-{i}.wav'
        write_wave(path, segment, sample_rate)

        result = model.transcribe(path, language=detected_language)

        segment_duration = len(segment) / sample_rate
        start_time = total_duration
        end_time = total_duration + segment_duration

        if result['text'].strip():  # 只有在有文本時才添加字幕
            segment_count += 1
            srt_entry = (
                f"{segment_count}\n"
                f"{format_timecode(start_time)} --> {format_timecode(end_time)}\n"
                f"{result['text'].strip()}\n\n"
            )
            srt_output.append(srt_entry)

            if debug:
                print(f"Segment {i}: {format_timecode(start_time)} --> {format_timecode(end_time)}")
                print(f"Text: {result['text'].strip()}\n")

        total_duration += segment_duration
        os.remove(path)

    os.remove(audio_file)

    # 將 SRT 內容寫入文件
    output_srt = os.path.splitext(video_file)[0] + ".srt"
    with open(output_srt, 'w', encoding='utf-8') as f:
        f.writelines(srt_output)

    print(f"SRT 文件已生成: {output_srt}")

if __name__ == '__main__':
    video_file = sys.argv[1]
    debug = len(sys.argv) > 2 and sys.argv[2].lower() == 'debug'
    main(video_file, debug)
