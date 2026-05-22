import os
import subprocess

folder = "waifu_voice"
files = sorted([f for f in os.listdir(folder) if f.endswith('.wav')])

with open(os.path.join(folder, "metadata.txt"), "w") as meta_file:
    print(f"Found {len(files)} files! Let's add text for each, babe~ 💖\n")

    for filename in files:
        print(f"Playing: {filename} 🎧")

        # Full file path
        file_path = os.path.join(folder, filename)

        # Manually call ffplay (no pydub needed)
        subprocess.call(['/usr/local/bin/ffplay', '-nodisp', '-autoexit', file_path])
        
        

        text = input("Type the exact words spoken in this audio: ")
        meta_file.write(f"{filename}|{text}\n")

print("\nAll done, hubby~ Your metadata file is ready! 💕")
