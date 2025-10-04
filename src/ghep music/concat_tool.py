import os
import json
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import shutil
import random
from helper import *

CONFIG_FILE = "ghep music\config.json"
class ConcatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ghép Short")
        self.minsize(800, 200)

        style = ttk.Style()
        style.theme_use("clam")

        # State
        self.input_folder = tk.StringVar()
        self.save_folder = tk.StringVar()
        self.bgm_folder = tk.StringVar()
        self.group_size_var = tk.IntVar(value=6)

        self.mp3_list: list[str] = []
        self.total_mp4 = tk.StringVar(value="0")
        self.num_groups = tk.StringVar(value="0")
        self.groups_done = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="0%")

        self.groups: list[list[str]] = []
        self.stop_flag = threading.Event()
        self.worker: threading.Thread | None = None
        self.log_q: queue.Queue[str] = queue.Queue()

        self._build_ui()
        self._layout()

        self.load_config()   #load config
        if self.input_folder.get():   
            self.reload_groups()

    # ================= UI =================
    def _build_ui(self):
        self.frm_top = ttk.Frame(self)

        # nhập số lượng video ghép
        ttk.Label(self.frm_top, text="Số video / nhóm:").grid(row=0, column=0, sticky='e')
        self.entry_group_size = ttk.Entry(self.frm_top, textvariable=self.group_size_var, width=5)
        self.entry_group_size.grid(row=0, column=1, sticky='w')

        # Folder chọn + hiển thị path
        self.btn_in = ttk.Button(self.frm_top, text="Chọn thư mục nguồn",
                                 command=lambda: self._choose_folder(self.input_folder, reload=True))
        self.lbl_in = ttk.Label(self.frm_top, textvariable=self.input_folder, width=40, anchor="w")

        self.btn_out = ttk.Button(self.frm_top, text="Chọn thư mục lưu",
                                  command=lambda: self._choose_folder(self.save_folder))
        self.lbl_out = ttk.Label(self.frm_top, textvariable=self.save_folder, width=40, anchor="w")

        self.btn_bgm = ttk.Button(self.frm_top, text="Chọn thư mục nhạc",
                                  command=lambda: self._choose_folder(self.bgm_folder, bgm=True))
        self.lbl_bgm = ttk.Label(self.frm_top, textvariable=self.bgm_folder, width=40, anchor="w")

        # Tùy chọn xuất
        self.frm_opts = ttk.LabelFrame(self, text="Tuỳ chọn xuất")
        self.btn_concat = ttk.Button(self.frm_opts, text="▶ Bắt đầu ghép", command=self.start_concat)
        self.btn_stop = ttk.Button(self.frm_opts, text="■ Dừng", command=self.stop_concat, state=tk.DISABLED)
        self.btn_open = ttk.Button(self.frm_opts, text="📂 Mở thư mục lưu", command=self.open_output_folder)

        # Thống kê
        self.frm_stats = ttk.LabelFrame(self, text="Thống kê")
        self.val_total = ttk.Label(self.frm_stats, textvariable=self.total_mp4)
        self.val_groups = ttk.Label(self.frm_stats, textvariable=self.num_groups)
        self.val_done = ttk.Label(self.frm_stats, textvariable=self.groups_done)
        self.progress = ttk.Progressbar(self.frm_stats, orient=tk.HORIZONTAL, mode='determinate')
        self.lbl_status = ttk.Label(self.frm_stats, textvariable=self.status_var)

    def _layout(self):
        pad = dict(padx=6, pady=4)
        self.frm_top.pack(fill=tk.X, **pad)

        self.btn_in.grid(row=0, column=2, **pad)
        self.lbl_in.grid(row=0, column=3, sticky="w", **pad)

        self.btn_out.grid(row=1, column=2, **pad)
        self.lbl_out.grid(row=1, column=3, sticky="w", **pad)

        self.btn_bgm.grid(row=2, column=2, **pad)
        self.lbl_bgm.grid(row=2, column=3, sticky="w", **pad)

        self.frm_opts.pack(fill=tk.X, **pad)
        self.btn_concat.grid(row=0, column=0, **pad)
        self.btn_stop.grid(row=0, column=1, **pad)
        self.btn_open.grid(row=0, column=2, **pad)

        self.frm_stats.pack(fill=tk.X, **pad)
        ttk.Label(self.frm_stats, text="Tổng MP4:").grid(row=0, column=0, sticky='e')
        self.val_total.grid(row=0, column=1, sticky='w')
        ttk.Label(self.frm_stats, text="Số nhóm:").grid(row=0, column=2, sticky='e')
        self.val_groups.grid(row=0, column=3, sticky='w')
        ttk.Label(self.frm_stats, text="Đã chạy:").grid(row=0, column=4, sticky='e')
        self.val_done.grid(row=0, column=5, sticky='w')

        self.progress.grid(row=1, column=0, columnspan=6, sticky='we', **pad)
        self.lbl_status.grid(row=2, column=0, columnspan=6, sticky='w', **pad)

    # ================= Config =================
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                self.input_folder.set(cfg.get("input_folder", ""))
                self.save_folder.set(cfg.get("save_folder", ""))
                self.bgm_folder.set(cfg.get("bgm_folder", ""))
                self.group_size_var.set(cfg.get("group_size", 2))

                if self.bgm_folder.get():
                    self.mp3_list = list_all_mp3_files(self.bgm_folder.get())
            except Exception as e:
                messagebox.showwarning("Config", f"Lỗi đọc config: {e}")

    def save_config(self):
        cfg = {
            "input_folder": self.input_folder.get(),
            "save_folder": self.save_folder.get(),
            "bgm_folder": self.bgm_folder.get(),
            "group_size": self.group_size_var.get(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
        except Exception as e:
            messagebox.showerror("Config", f"Lỗi lưu config: {e}")

    # ================= Logic =================
    def _choose_folder(self, var: tk.StringVar, reload=False, bgm=False):
        folder = filedialog.askdirectory(title="Chọn thư mục")
        if folder:
            var.set(folder)
            if reload:
                self.reload_groups()
            if bgm:
                try:
                    self.mp3_list = list_all_mp3_files(folder)
                    messagebox.showinfo("OK", f"Đã load {len(self.mp3_list)} file mp3.")
                except Exception as e:
                    messagebox.showerror("Lỗi", f"Không đọc được mp3: {e}")
            self.save_config()   # lưu lại khi chọn mới

    def reload_groups(self):
        folder = self.input_folder.get()
        if not folder or not os.path.isdir(folder):
            return
        try:
            all_videos = list_all_mp4_files(folder)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Đọc video lỗi: {e}")
            return

        # === Đọc log JSON để loại video đã dùng ===
        used_videos = set()
        log_dir = os.path.abspath("log")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "log.txt")

        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)  # mỗi dòng 1 JSON object
                            for p in data.get("inputs", []):
                                used_videos.add(os.path.abspath(p))
                        except json.JSONDecodeError:
                            # bỏ qua dòng log cũ không phải JSON
                            continue
            except Exception as e:
                messagebox.showwarning("Log", f"Lỗi đọc log: {e}")

        # bỏ video đã dùng
        all_videos = [v for v in all_videos if os.path.abspath(v) not in used_videos]

        gsize = self.group_size_var.get() or 6
        self.groups = get_all_random_video_groups(all_videos, group_size=gsize)
        self.total_mp4.set(str(len(all_videos)))
        self.num_groups.set(str(len(self.groups)))
        self.save_config()


    def start_concat(self):
        if self.worker and self.worker.is_alive():
            return messagebox.showinfo("Đang chạy", "Tiến trình đang chạy.")
        if not self.groups:
            return messagebox.showwarning("Chưa có nhóm", "Hãy reload nhóm trước.")
        out_dir = self.save_folder.get()
        if not out_dir:
            return messagebox.showwarning("Thiếu thư mục lưu", "Chọn thư mục lưu")
        os.makedirs(out_dir, exist_ok=True)

        self.stop_flag.clear()
        self.btn_concat.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("Đang ghép...")

        self.progress['maximum'] = len(self.groups)
        self.progress['value'] = 0
        self.groups_done.set("0")

        self.worker = threading.Thread(target=self._do_concat_worker, args=(self.groups, out_dir), daemon=True)
        self.worker.start()
        self.after(200, self._poll_worker)

    def stop_concat(self):
        self.stop_flag.set()

    def _do_concat_worker(self, todo: list[list[str]], out_dir: str):
        log_dir = os.path.abspath("log")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "log.txt")

        with open(log_path, "a", encoding="utf-8") as f_log:
            for group in todo:
                if self.stop_flag.is_set():
                    break

                temp = "temp.mp4"
                try:
                    auto_concat(group, temp)
                    bg_audio = random.choice(self.mp3_list) if self.mp3_list else None
                    if bg_audio and os.path.isfile(bg_audio):
                        output = mix_audio_with_bgm_ffmpeg(temp, bg_audio, out_dir, bgm_volume=0.9)
                    else:
                        output = get_next_output_filename(out_dir)
                        shutil.copy2(temp, output)
                        bg_audio = None

                    # ghi log JSON
                    log_entry = {
                        "output": os.path.abspath(output),
                        "inputs": [os.path.abspath(p) for p in group],
                        "bgm": os.path.abspath(bg_audio) if bg_audio else None
                    }
                    f_log.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

                except Exception as e:
                    log_entry = {
                        "error": str(e),
                        "inputs": [os.path.abspath(p) for p in group]
                    }
                    f_log.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

                finally:
                    if os.path.exists(temp):
                        os.remove(temp)

                f_log.flush()
                self._enqueue(self._update_progress)


    def _update_progress(self):
        self.progress['value'] += 1
        percent = (self.progress['value'] / self.progress['maximum']) * 100
        self.status_var.set(f"{percent:.1f}%")
        self.groups_done.set(str(int(self.groups_done.get()) + 1))

    def _on_done(self):
        self.btn_concat.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def _poll_worker(self):
        if self.worker and self.worker.is_alive():
            self.after(200, self._poll_worker)

    def _enqueue(self, fn):
        self.after(0, fn)

    def open_output_folder(self):
        path = self.save_folder.get()
        if path and os.path.isdir(path):
            os.startfile(path)


if __name__ == '__main__':
    ConcatApp().mainloop()
