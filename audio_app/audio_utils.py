"""
Audio feature extraction: given a path to an audio file, extract
duration, sample rate, bitrate, loudness, and a rough noise/quality
estimate (bonus).
"""
import os
import numpy as np
import librosa
from pydub import AudioSegment


def extract_audio_features(file_path):
    y, sr = librosa.load(file_path, sr=None, mono=True)
    duration_sec = float(librosa.get_duration(y=y, sr=sr))

    audio = AudioSegment.from_file(file_path)
    file_size_bits = os.path.getsize(file_path) * 8
    bitrate_kbps = (file_size_bits / duration_sec) / 1000 if duration_sec > 0 else 0

    rms = np.sqrt(np.mean(y ** 2)) if len(y) else 0
    loudness_db = float(20 * np.log10(rms)) if rms > 0 else -120.0

    frame_length, hop_length = 2048, 512
    if len(y) >= frame_length:
        rms_frames = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        noise_floor = np.percentile(rms_frames, 10)
        signal_peak = np.percentile(rms_frames, 90)
        noise_estimate_db = float(20 * np.log10(signal_peak / noise_floor)) if noise_floor > 0 else None
    else:
        noise_estimate_db = None

    return {
        "duration_sec": round(duration_sec, 2),
        "sample_rate_hz": int(sr),
        "bitrate_kbps": round(bitrate_kbps, 1),
        "loudness_db": round(loudness_db, 2),
        "noise_estimate_db": round(noise_estimate_db, 2) if noise_estimate_db is not None else None,
    }