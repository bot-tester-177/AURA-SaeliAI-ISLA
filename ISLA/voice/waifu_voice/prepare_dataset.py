#!/usr/bin/env python3
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'my_waifu_dataset'
PRE = ROOT / 'wavs_preprocessed'
SRC = ROOT / 'wavs'
METADATA = ROOT / 'metadata.csv'

OUT.mkdir(exist_ok=True)

def main():
    # copy metadata
    if METADATA.exists():
        shutil.copy2(METADATA, OUT / 'metadata.csv')
        print('Copied metadata.csv to', OUT)
    else:
        print('metadata.csv not found in', ROOT)

    src_dir = PRE if PRE.exists() and any(PRE.glob('*.wav')) else SRC
    if not src_dir.exists():
        print('No source WAV directory found at', src_dir)
        return

    for p in sorted(src_dir.glob('*.wav')):
        shutil.copy2(p, OUT / p.name)
    print(f'Copied {len(list(src_dir.glob("*.wav")))} WAVs to', OUT)

if __name__ == '__main__':
    main()
