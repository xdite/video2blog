import webrtcvad
import wave
import contextlib
import collections
import sys
import whisper
import numpy as np

def read_wave(path):
    with contextlib.closing(wave.open(path, 'rb')) as wf:
        num_channels = wf.getnchannels()
        assert num_channels == 1
        sample_width = wf.getsampwidth()
        assert sample_width == 2
        sample_rate = wf.getframerate()
        assert sample_rate in (8000, 16000, 32000, 48000)
        pcm_data = wf.readframes(wf.getnframes())
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

def main(audio_file):
    # 加載 whisper 模型
    model = whisper.load_model("base")

    # 讀取音頻文件
    audio, sample_rate = read_wave(audio_file)

    # 創建 VAD 對象
    vad = webrtcvad.Vad(3)  # 設置 VAD 的激進程度 (0-3)

    # 分割音頻
    frames = frame_generator(30, audio, sample_rate)
    segments = vad_collector(sample_rate, 30, 300, vad, frames)

    # 處理每個語音片段
    for i, segment in enumerate(segments):
        # 將片段保存為臨時文件
        path = f'chunk-{i}.wav'
        write_wave(path, segment, sample_rate)

        # 使用 whisper 處理音頻段
        result = model.transcribe(path)

        # 輸出字幕
        print(f"Segment {i}: {result['text']}")

        # 刪除臨時文件
        os.remove(path)

def write_wave(path, audio, sample_rate):
    with contextlib.closing(wave.open(path, 'wb')) as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio)

if __name__ == '__main__':
    audio_file = sys.argv[1]
    main(audio_file)
