import os.path

import librosa
from librosa import feature


def analyze_track(file_path):
    """
    Analyze an audio file for key (Major/Minor) and BPM with better key detection.
    """
    print(f"Analyzing: {file_path}")

    print("Load audio file")
    y, sr = librosa.load(file_path, sr=None, duration=30)

    print("Estimate tempo (BPM)")
    onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=1024)
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr, onset_envelope=onset_env, hop_length=1024)

    print("Estimate key using chroma features")
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)  # Mean chroma activation per note
    key_index = chroma_mean.argmax()  # Most dominant note (tonic)

    print("Find second most dominant note (to check relative minor/major)")
    chroma_mean[key_index] = 0  # Temporarily zero out primary key to get 2nd strongest
    second_index = chroma_mean.argmax()

    # Key name mappings
    key_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

    detected_key = key_names[key_index]

    print("Determine Major/Minor based on second strongest note")
    relative_minor_index = (key_index + 9) % 12  # Major → Minor shift (e.g., C → A)
    relative_major_index = (key_index + 3) % 12  # Minor → Major shift (e.g., A → C)

    if second_index == relative_minor_index:
        key_type = "Minor"
    elif second_index == relative_major_index:
        key_type = "Major"
    else:
        key_type = "Unclear"  # If we can't determine with confidence

    print(f"Detected Key: {detected_key} {key_type}")
    print(f"Estimated BPM: {round(tempo.item())}")

    return {"file": file_path, "key": detected_key, "mode": key_type, "bpm": round(tempo.item())}


# Test a track
test_track = os.path.normpath(r"C:\Users\wyrmwood\Dropbox\public\music\Ambient-Dark\Flickering Shadows.mp3")
result = analyze_track(test_track)
