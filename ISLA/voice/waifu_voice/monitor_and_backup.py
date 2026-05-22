#!/usr/bin/env python3
import os
import time
import shutil
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(ROOT, "my_waifu_model")
BACKUP_DIR = os.path.join(MODEL_DIR, "backups")
TRAIN_LOG = os.path.join(ROOT, "train.log")


def find_checkpoints(model_dir):
    if not os.path.isdir(model_dir):
        return []
    entries = []
    for name in os.listdir(model_dir):
        path = os.path.join(model_dir, name)
        if os.path.isdir(path) or name.endswith(('.pth', '.pt', '.tar', '.ckpt')):
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                mtime = 0
            entries.append((mtime, name, path))
    entries.sort(reverse=True)
    return entries


def backup_path_for(src_path):
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = os.path.basename(src_path.rstrip(os.sep))
    dest = os.path.join(BACKUP_DIR, f"backup_{ts}_{base}")
    return dest


def copy_checkpoint(src):
    os.makedirs(BACKUP_DIR, exist_ok=True)
    dest = backup_path_for(src)
    try:
        if os.path.isdir(src):
            shutil.copytree(src, dest)
        else:
            shutil.copy2(src, dest)
        print(f"Backed up checkpoint {src} -> {dest}", flush=True)
    except Exception as e:
        print(f"Failed to backup {src}: {e}", flush=True)


def tail_log_and_watch(interval=5):
    known = set()
    # initialize known
    for _, name, path in find_checkpoints(MODEL_DIR):
        known.add(name)

    # open train log if exists
    log_f = None
    if os.path.isfile(TRAIN_LOG):
        try:
            log_f = open(TRAIN_LOG, 'r', encoding='utf-8', errors='replace')
            log_f.seek(0, os.SEEK_END)
        except Exception:
            log_f = None

    print("Starting monitor: watching model dir and tailing train.log", flush=True)
    try:
        while True:
            # check checkpoints
            entries = find_checkpoints(MODEL_DIR)
            for _, name, path in entries:
                if name not in known:
                    print(f"New checkpoint detected: {name}", flush=True)
                    copy_checkpoint(path)
                    known.add(name)

            # tail log
            if log_f:
                where = log_f.tell()
                line = log_f.readline()
                while line:
                    print(line, end='', flush=True)
                    line = log_f.readline()
                # if file was truncated (rotated), seek to start
                if log_f.tell() < where:
                    log_f.seek(0, os.SEEK_END)
            else:
                if os.path.isfile(TRAIN_LOG):
                    try:
                        log_f = open(TRAIN_LOG, 'r', encoding='utf-8', errors='replace')
                        log_f.seek(0, os.SEEK_END)
                        print(f"Attached to {TRAIN_LOG}", flush=True)
                    except Exception:
                        log_f = None

            time.sleep(interval)
    except KeyboardInterrupt:
        print("Monitor stopped by user", flush=True)
    finally:
        if log_f:
            log_f.close()


if __name__ == '__main__':
    tail_log_and_watch()
