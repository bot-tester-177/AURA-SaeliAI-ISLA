import os
import sys
import threading
import subprocess
import queue
import time
import shutil
from datetime import datetime
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except Exception:
    print("tkinter is required to run this monitor GUI")
    raise


ROOT = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(ROOT, "waifu-env", "bin", "python")
TRAIN_SCRIPT = os.path.join(ROOT, "train_waifu.py")
MODEL_DIR = os.path.join(ROOT, "my_waifu_model")
BACKUP_DIR = os.path.join(MODEL_DIR, "backups")


def find_checkpoints(model_dir):
    if not os.path.isdir(model_dir):
        return []
    entries = []
    for name in os.listdir(model_dir):
        path = os.path.join(model_dir, name)
        # consider dirs or files that look like checkpoints
        if os.path.isdir(path) or name.endswith(('.pth', '.pt', '.tar', '.ckpt')):
            try:
                mtime = os.path.getmtime(path)
            except Exception:
                mtime = 0
            entries.append((mtime, name, path))
    entries.sort(reverse=True)
    return entries


class TrainMonitor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Waifu Training Monitor")
        self.geometry("1000x700")

        self.proc = None
        self.output_queue = queue.Queue()
        self.polling = False

        self._build_ui()
        self.after(200, self._flush_output)
        self._start_dir_poller()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)

        self.start_btn = ttk.Button(top, text="Start Training", command=self.start_training)
        self.start_btn.pack(side="left")

        self.stop_btn = ttk.Button(top, text="Stop Training", command=self.stop_training)
        self.stop_btn.pack(side="left", padx=6)

        self.save_btn = ttk.Button(top, text="Save Checkpoint Backup", command=self.save_checkpoint)
        self.save_btn.pack(side="left", padx=6)

        self.open_dir_btn = ttk.Button(top, text="Open Model Dir", command=self.open_model_dir)
        self.open_dir_btn.pack(side="left", padx=6)

        mid = ttk.PanedWindow(self, orient="horizontal")
        mid.pack(fill="both", expand=True, padx=8, pady=6)

        # Log text
        log_frame = ttk.Frame(mid)
        self.log_text = tk.Text(log_frame, wrap="none")
        self.log_text.pack(fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")

        # Checkpoints list
        side_frame = ttk.Frame(mid, width=300)
        ttk.Label(side_frame, text="Checkpoints (latest first)").pack(anchor="w")
        self.ck_list = tk.Listbox(side_frame)
        self.ck_list.pack(fill="both", expand=True)
        mid.add(log_frame, weight=3)
        mid.add(side_frame, weight=1)

        status = ttk.Frame(self)
        status.pack(fill="x", padx=8, pady=6)
        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(status, textvariable=self.status_var).pack(side="left")

    def _flush_output(self):
        try:
            while True:
                line = self.output_queue.get_nowait()
                self.log_text.insert("end", line)
                self.log_text.see("end")
        except queue.Empty:
            pass
        self.after(200, self._flush_output)

    def _reader_thread(self, stream):
        for raw in iter(stream.readline, b""):
            try:
                line = raw.decode(errors='replace')
            except Exception:
                line = str(raw)
            self.output_queue.put(line)
        try:
            stream.close()
        except Exception:
            pass

    def start_training(self):
        if self.proc and self.proc.poll() is None:
            messagebox.showinfo("Training", "Training already running")
            return
        if not os.path.isfile(VENV_PY):
            messagebox.showerror("Error", f"Python not found: {VENV_PY}")
            return
        if not os.path.isfile(TRAIN_SCRIPT):
            messagebox.showerror("Error", f"Train script not found: {TRAIN_SCRIPT}")
            return

        env = os.environ.copy()
        env.setdefault("OMP_NUM_THREADS", "1")
        env.setdefault("MKL_NUM_THREADS", "1")
        env.setdefault("OPENBLAS_NUM_THREADS", "1")
        env.setdefault("NUMEXPR_NUM_THREADS", "1")

        cmd = ["nice", "-n", "10", VENV_PY, TRAIN_SCRIPT]
        self.log_text.insert("end", f"Starting: {' '.join(cmd)}\n")
        self.log_text.see("end")
        self.proc = subprocess.Popen(cmd, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=env)
        threading.Thread(target=self._reader_thread, args=(self.proc.stdout,), daemon=True).start()
        self.status_var.set("Training: running")

    def stop_training(self):
        if not self.proc or self.proc.poll() is not None:
            messagebox.showinfo("Training", "No running training process")
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=5)
            self.log_text.insert("end", "\nTraining process terminated.\n")
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.log_text.insert("end", "\nTraining process killed.\n")
        self.status_var.set("Idle")

    def open_model_dir(self):
        if not os.path.isdir(MODEL_DIR):
            messagebox.showinfo("Model Dir", f"No model dir at {MODEL_DIR}")
            return
        if sys.platform == 'darwin':
            subprocess.Popen(["open", MODEL_DIR])
        elif sys.platform == 'win32':
            subprocess.Popen(["explorer", MODEL_DIR])
        else:
            subprocess.Popen(["xdg-open", MODEL_DIR])

    def save_checkpoint(self):
        entries = find_checkpoints(MODEL_DIR)
        if not entries:
            messagebox.showinfo("Save Checkpoint", "No checkpoints found to backup.")
            return
        latest = entries[0][2]
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(BACKUP_DIR, exist_ok=True)
        dest = os.path.join(BACKUP_DIR, f"backup_{ts}_{os.path.basename(latest)}")
        try:
            if os.path.isdir(latest):
                shutil.copytree(latest, dest)
            else:
                shutil.copy2(latest, dest)
            messagebox.showinfo("Save Checkpoint", f"Saved backup to {dest}")
        except Exception as e:
            messagebox.showerror("Save Checkpoint", str(e))

    def _start_dir_poller(self):
        def poll():
            while True:
                entries = find_checkpoints(MODEL_DIR)
                names = [f"{datetime.fromtimestamp(m).isoformat()}  {n}" for (m, n, p) in entries]
                # update listbox in main thread
                def update():
                    self.ck_list.delete(0, 'end')
                    for n in names:
                        self.ck_list.insert('end', n)
                self.after(0, update)
                time.sleep(5)
        t = threading.Thread(target=poll, daemon=True)
        t.start()


if __name__ == '__main__':
    app = TrainMonitor()
    app.mainloop()
