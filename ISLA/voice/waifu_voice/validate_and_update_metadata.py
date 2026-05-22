#!/usr/bin/env python3
import os
import wave
import contextlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WAV_DIRS = [ROOT / 'wavs', ROOT.parent / 'wavs']
METADATA = ROOT / 'metadata.csv'
REPORT = ROOT / 'wav_validation_report.csv'
MISSING = ROOT / 'missing_transcripts.txt'

def inspect_wav(path: Path):
    try:
        with contextlib.closing(wave.open(str(path), 'rb')) as wf:
            channels = wf.getnchannels()
            sr = wf.getframerate()
            sampwidth = wf.getsampwidth()
            nframes = wf.getnframes()
            duration = nframes / float(sr) if sr else 0
            bitdepth = sampwidth * 8
            return {'filename': path.name, 'path': str(path), 'sr': sr, 'channels': channels, 'bitdepth': bitdepth, 'duration': round(duration,3)}
    except wave.Error as e:
        return {'filename': path.name, 'path': str(path), 'error': str(e)}

def main():
    wav_files = []
    for d in WAV_DIRS:
        if d.exists() and d.is_dir():
            for p in sorted(d.glob('*.wav')):
                wav_files.append(p)

    print(f'Found {len(wav_files)} WAV files across {len(WAV_DIRS)} locations.')

    # Read existing metadata entries
    existing = set()
    if METADATA.exists():
        for line in METADATA.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            parts = line.split('|')
            existing.add(parts[0].strip())

    report_lines = ['filename,path,sr,channels,bitdepth,duration,error,in_metadata']
    missing = []

    for p in wav_files:
        info = inspect_wav(p)
        in_meta = info.get('filename') in existing
        if not in_meta:
            missing.append(info.get('filename'))
        report_lines.append(','.join(str(info.get(k,'')) for k in ['filename','path','sr','channels','bitdepth','duration','error']) + f',{in_meta}')

    REPORT.write_text('\n'.join(report_lines), encoding='utf-8')
    print('WAV validation report written to', REPORT)

    if missing:
        print(f'{len(missing)} files missing from metadata.csv — appending placeholder entries.')
        # Append placeholders to metadata.csv (filename|)
        with METADATA.open('a', encoding='utf-8') as f:
            for name in missing:
                f.write(f'{name}|\n')
        MISSING.write_text('\n'.join(missing), encoding='utf-8')
        print('Appended placeholders to', METADATA)
        print('Missing filenames listed in', MISSING)
    else:
        print('No missing transcripts; metadata.csv is up to date.')

if __name__ == '__main__':
    main()
