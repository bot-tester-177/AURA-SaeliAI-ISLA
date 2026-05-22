from faster_whisper import WhisperModel
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"


# Babe~ pick your model size: "base", "small", "medium", or "large"
model = WhisperModel("base", device="cpu", compute_type="int8")

# Where all your sweet waifu voice files are stored~
folder = "waifu_voice"

# Where we’ll save the transcriptions, love~
output_file = "waifu_voice/metadata.txt"

files = sorted([f for f in os.listdir(folder) if f.endswith(".wav")])
print(f"Found {len(files)} files, babe~ Let’s start transcribing 💖")

with open(output_file, "w") as meta:
    for file in files:
        file_path = os.path.join(folder, file)
        print(f"\nTranscribing: {file} 🎧")

        segments, _ = model.transcribe(file_path)

        text = ""
        for segment in segments:
            text += segment.text.strip() + " "

        text = text.strip()
        print(f"💬 Transcription: {text}")

        meta.write(f"{file}|{text}\n")

print("\nAll done babe~ I’ve written everything down just for you 💕✨")
