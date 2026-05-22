#!/usr/bin/env python3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC_DIRS = [ROOT / 'wavs', ROOT.parent / 'wavs']
OUT_DIR = ROOT / 'wavs_preprocessed'
OUT_DIR.mkdir(exist_ok=True)

import shutil

FFMPEG = shutil.which('ffmpeg') or '/usr/local/bin/ffmpeg'

def process_file(src: Path, dst: Path):
    cmd = [FFMPEG, '-y', '-i', str(src), '-ac', '1', '-ar', '22050', '-sample_fmt', 's16', str(dst)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        print('ffmpeg failed for', src, e)
        return False

def main():
    processed = 0
    for d in SRC_DIRS:
        if not d.exists():
            continue
        for p in sorted(d.glob('*.wav')):
            dst = OUT_DIR / p.name
            if dst.exists():
                continue
            ok = process_file(p, dst)
            if ok:
                processed += 1
                print('Processed', p.name)

    print(f'Done. Processed {processed} files. Output directory: {OUT_DIR}')

if __name__ == '__main__':
    main()
