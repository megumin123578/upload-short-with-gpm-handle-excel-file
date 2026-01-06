from .helper import *
from .concat_page_ui import ConcatPageUIMixin
from ui_theme import setup_theme

class ConcatPage(tk.Frame, ConcatPageUIMixin):
    def __init__(self, parent):
        super().__init__(parent)

        self._loading = False
        self._reload_token = 0
        self._reload_thread: threading.Thread | None = None

        # Configure style
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Accent.TButton", font=("Trebuchet MS", 10, "bold"), foreground="#ffffff", background="#4CAF50", padding=6)
        style.configure("Stop.TButton", font=("Trebuchet MS", 10, "bold"), foreground="#ffffff", background="#F44336", padding=6)
        style.configure("Secondary.TButton", font=("Trebuchet MS", 10), foreground="#ffffff", background="#2196F3", padding=6)
        style.configure("TLabel", font=("Trebuchet MS", 10))
        style.configure("TEntry", font=("Trebuchet MS", 10))
        style.configure("TCombobox", font=("Trebuchet MS", 10))

        style.configure("NvencOn.TButton", font=("Trebuchet MS", 10, "bold"), foreground="#ffffff", background="#4CAF50")
        style.map("NvencOn.TButton", background=[("active", "#45a049")])

        style.configure("NvencOff.TButton", font=("Trebuchet MS", 10, "bold"), foreground="#ffffff", background="#d32f2f")
        style.map("NvencOff.TButton", background=[("active", "#b71c1c")])
        style.configure(
            "Advanced.TButton",
            font=("Trebuchet MS", 10, "bold"),
            foreground="#ffffff",
            background="#D13BFF",
            padding=6,
        )
        style.map(
            "Advanced.TButton",
            background=[("active", "#8BC34A")]
        )

        style.configure(
            "Advanced.On.TButton",
            font=("Trebuchet MS", 10, "bold"),
            foreground="#ffffff",
            background="#8BC34A",   
            padding=6,
        )
        style.map(
            "Advanced.On.TButton",
            background=[("active", "#D13BFF")]
        )


        self.start_time = None
        self.elapsed_times = []

        # State
        self.input_folder = tk.StringVar()
        self.save_folder = tk.StringVar()
        self.bgm_folder = tk.StringVar()
        self.group_size_var = tk.IntVar(value=6)
        self.bgm_volume_var = tk.DoubleVar(value=0.5)
        self.video_volume_var = tk.DoubleVar(value=0.2)
        self.main_video_volume_var = tk.DoubleVar(value=1.0)
        self.limit_videos_var = tk.IntVar(value=0)
        
        self.concat_mode = tk.StringVar(value="Concat with music background")

        # ==== Video settings ====
        self.resolution_var = tk.StringVar(value="1080x1920")
        self.fps_var = tk.IntVar(value=60)
        self.use_nvenc_var = tk.BooleanVar(value=True)
        self.cq_var = tk.IntVar(value=23)
        self.v_bitrate_var = tk.StringVar(value="12M")
        self.a_bitrate_var = tk.StringVar(value="160k")
        self.nvenc_preset_var = tk.StringVar(value="p4")

        self.mp3_list: list[str] = []
        self.total_mp4 = tk.StringVar(value="0")
        self.num_groups = tk.StringVar(value="0")
        self.groups_done = tk.StringVar(value="0")
        self.status_var = tk.StringVar(value="Idle")
        self.last_output_var = tk.StringVar(value="(chưa có)")
        self.groups: list[list[str]] = []
        self.stop_flag = threading.Event()
        self.worker: threading.Thread | None = None
        self.log_q: queue.Queue[str] = queue.Queue()
        os.makedirs(CONFIG_DIR, exist_ok=True)
        self.selected_channel = tk.StringVar()

        self._advanced = False
        self.time_limit_min_var = tk.StringVar(value="0")
        self.time_limit_sec_var = tk.StringVar(value="0")

        self.outro_mode_var = tk.StringVar(value="By group count")
        self.outro_duration_var = tk.IntVar(value=15)

        self.cut_scope_var = tk.StringVar(value="first")
        self.cut_frame_first_var = tk.StringVar(value="0")
        self.cut_frame_last_var = tk.StringVar(value="0")

        self._tag_id = 0

        self._build_ui()
        self.cut_frame_first_var.trace_add("write", lambda *_: self.save_channel_config())
        self.cut_frame_last_var.trace_add("write", lambda *_: self.save_channel_config())
        self._layout()
        self.bind("<Delete>", self._on_global_delete) 

        self.load_last_channel()
        if self.input_folder.get():
            self.reload_groups()

    def _build_ui(self):
        ConcatPageUIMixin._build_ui(self)

    def _add_folder_row(self, label, var, row, parent, reload=False, bgm=False):
        return ConcatPageUIMixin._add_folder_row(self, label, var, row, parent, reload=reload, bgm=bgm)

    def _layout(self):
        ConcatPageUIMixin._layout(self)

    def _update_volume_label(self, *args):
        val = self.bgm_volume_var.get()
        self.lbl_volume.config(text=f"{val * 100:.0f}%")
        self.save_channel_config()

    def _append_log(self, text: str):
        self.txt_log.configure(state="normal")
        if text.startswith("Đã ghép xong: "):
            path = text.replace("Đã ghép xong: ", "").strip()
            self._tag_id += 1
            tag_name = f"link_{self._tag_id}"

            # In tiền tố + path, nhưng path có tag riêng
            self.txt_log.insert("end", "Đã ghép xong: ")
            self.txt_log.insert("end", path + "\n", tag_name)

            # Trang điểm tag + bind sự kiện click
            self.txt_log.tag_configure(tag_name, foreground="#32CD32", underline=True)
            self.txt_log.tag_bind(tag_name, "<Enter>",  lambda e: self.txt_log.config(cursor="hand2"))
            self.txt_log.tag_bind(tag_name, "<Leave>",  lambda e: self.txt_log.config(cursor=""))
            self.txt_log.tag_bind(tag_name, "<Button-1>", lambda e, p=path: self._open_video_path(p))
        else:
            self.txt_log.insert("end", text + "\n")
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")


    def reload_groups(self):
        folder = self.input_folder.get()
        if not folder or not os.path.isdir(folder):
            self.groups = []
            self.total_mp4.set("0")
            self._loading = False
            if self.concat_mode.get() in ("Concat with time limit", "Loop"):
                planned = self.limit_videos_var.get() or 1
                self.num_groups.set(str(planned))
            else:
                self.num_groups.set("0")

            return

        self._reload_token += 1
        token = self._reload_token
        self._loading = True
        self.total_mp4.set("Loading...")
        self.num_groups.set("Loading...")

        used_videos = self._get_used_videos_from_log()
        used_videos_lower = {p.lower() for p in used_videos}
        limit_groups = self.limit_videos_var.get()
        mode = self.concat_mode.get()
        gsize = self.group_size_var.get() or 6
        time_limit_min = self.time_limit_min_var.get()
        time_limit_sec = self.time_limit_sec_var.get()

        def worker():
            try:
                all_videos = list_all_mp4_files(folder, exclude_set=used_videos_lower)

                groups: list[list[str]] = []
                total_mp4 = len(all_videos)
                num_groups = 0

                if mode not in ("Concat with time limit", "Tuan Seo Custom", "Loop"):
                    all_groups = get_all_random_video_groups(all_videos, group_size=gsize)
                    groups = all_groups[:limit_groups] if limit_groups > 0 else all_groups
                    num_groups = len(groups)

                if mode == "Concat with time limit":
                    target_seconds = float(time_limit_min) * 60.0 + float(time_limit_sec)
                    estimated = estimate_time_limit_groups(all_videos, target_seconds)
                    if limit_groups > 0:
                        estimated = min(limit_groups, estimated)
                    num_groups = estimated
                elif mode == "Tuan Seo Custom":
                    filtered = [
                        v for v in all_videos
                        if os.path.basename(os.path.dirname(v)).lower() != "ok"
                    ]
                    total_mp4 = len(filtered)
                    target_seconds = float(time_limit_min) * 60.0 + float(time_limit_sec)
                    estimated = estimate_time_limit_groups(filtered, target_seconds)
                    if limit_groups > 0:
                        estimated = min(limit_groups, estimated)
                    num_groups = estimated
                elif mode == "Loop":
                    remaining = len(all_videos)
                    if limit_groups > 0:
                        remaining = min(remaining, limit_groups)
                    num_groups = remaining

                def apply():
                    if token != self._reload_token:
                        return
                    self.groups = groups
                    self.total_mp4.set(str(total_mp4))
                    self.num_groups.set(str(num_groups))
                    self._loading = False

                self.after(0, apply)
            except Exception as e:
                def apply_error():
                    if token != self._reload_token:
                        return
                    self._loading = False
                    messagebox.showerror("L?i", f"D?c video l?i: {e}")
                    self.total_mp4.set("0")
                    self.num_groups.set("0")

                self.after(0, apply_error)

        self._reload_thread = threading.Thread(target=worker, daemon=True)
        self._reload_thread.start()

    def _choose_folder(self, var: tk.StringVar, reload=False, bgm=False):
        folder = filedialog.askdirectory(title="Select folder")
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
            self.save_channel_config(force=True)

    def start_concat(self):
        self.start_time = time.time()
        self.elapsed_times.clear()
        if self._loading:
            return messagebox.showinfo("Dang load", "Dang load danh s?ch video, vui l?ng d?i.")
        mode = self.concat_mode.get()
        if self.worker and self.worker.is_alive():
            return messagebox.showinfo("Đang chạy", "Tiến trình đang chạy.")
        NEED_PREBUILT_GROUPS = {
            "Concat with music background",
            "Normal concat (no music)",
            "Concat and Reverse",
            "Concat with outro music",   # vì mode này vẫn dùng group size khi chọn “By group count”
        }

        if mode in NEED_PREBUILT_GROUPS and not self.groups:
            return messagebox.showwarning("Đã chạy hết toàn bộ", "Hãy xóa log để gen lại.")
        out_dir = self.save_folder.get()
        if not out_dir:
            return messagebox.showwarning("Thiếu thư mục lưu", "Chọn thư mục lưu")
        os.makedirs(out_dir, exist_ok=True)
        limit_groups = self.limit_videos_var.get()
        mode = self.concat_mode.get()

        
        if mode == "Loop":
            folder = self.input_folder.get()
            used_global = {p.lower() for p in self._get_used_videos_from_log()}
            all_videos = list_all_mp4_files(folder, exclude_set=used_global) if folder and os.path.isdir(folder) else []
            pool = all_videos

            count = limit_groups if limit_groups > 0 else len(pool)
            if count <= 0:
                return messagebox.showwarning("Không còn video", "Hết clip để chạy Loop (hoặc chưa chọn nguồn).")
            todo_groups = [[] for _ in range(count)]

        elif mode == "Concat with time limit" or mode == "Tuan Seo Custom":
            folder = self.input_folder.get()
            used_global = {p.lower() for p in self._get_used_videos_from_log()}
            all_videos = list_all_mp4_files(folder, exclude_set=used_global) if folder and os.path.isdir(folder) else []

            if mode == "Tuan Seo Custom":
                all_videos = [
                    v for v in all_videos
                    if os.path.basename(os.path.dirname(v)).lower() != "ok"
                ]

            pool = all_videos

            target_seconds = float(self.time_limit_min_var.get()) * 60.0 + float(self.time_limit_sec_var.get())
            estimated = estimate_time_limit_groups(pool, target_seconds)

            if limit_groups > 0:
                count = min(limit_groups, estimated)
            else:
                count = estimated

            if count <= 0:
                return messagebox.showwarning("Không còn video", "Hết clip phù hợp cho Time Limit.")

            todo_groups = [[] for _ in range(count)]


        else:
            todo_groups = self.groups
            if limit_groups > 0:
                todo_groups = self.groups[:limit_groups]
        self.stop_flag.clear()
        self.btn_concat.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.status_var.set("Working...")
        self.progress['maximum'] = len(todo_groups)
        self.progress['value'] = 0
        self.progress_infor_var.set("Bắt đầu...")
        self.groups_done.set("0")
        self.worker = threading.Thread(target=self._do_concat_worker, args=(todo_groups, out_dir), daemon=True)
        self.worker.start()
        self.after(1000, self._poll_worker)

    def stop_concat(self):
        self.stop_flag.set()
        self.status_var.set("Stop")

    def _encode_group_to_temp(self, group: list[str], temp: str):
        width, height = map(int, self.resolution_var.get().split("x"))
        trim_specs = self._build_trim_specs(group)

        auto_concat(
            group, temp,
            num_threads=8,
            width=width,
            height=height,
            fps=self.fps_var.get(),
            use_nvenc=self.use_nvenc_var.get(),
            cq=self.cq_var.get(),
            v_bitrate=self.v_bitrate_var.get(),
            a_bitrate=self.a_bitrate_var.get(),
            nvenc_preset=self.nvenc_preset_var.get(),
            trim_specs=trim_specs,
        )

    #==============Switch mode================
    def _do_concat_worker(self, todo: list[list[str]], out_dir: str):
        log_dir = os.path.abspath("log")
        os.makedirs(log_dir, exist_ok=True)
        ch = self.selected_channel.get().strip() or 'default'
        log_path = os.path.join(log_dir, f"{ch}.txt")
        with open(log_path, "a", encoding="utf-8") as f_log:
            used_global = self._get_used_videos_from_log()  # đã dùng từ trước
            used_this_run = set()                            # dùng trong phiên chạy hiện tại
            for idx, group in enumerate(todo, 1):
                if self.stop_flag.is_set():
                    break
                start_group_time = time.time()
                temp = f"temp_{threading.get_ident()}.mp4"
                tmp_out = None
                output = None

                try:
                    mode = self.concat_mode.get()
                    total_jobs = len(todo)
                    if mode == "Loop":
                        self._enqueue(lambda i=idx, t=total_jobs: self._job_progress_start(i, t))
                    output = None

                    #++++++++++++++++LOGIC+++++++++++++++++++++
                    if mode == "Concat with music background":
                        self._encode_group_to_temp(group, temp)
                        bg_audio = random.choice(self.mp3_list) if self.mp3_list else None
                        desired = get_first_vids_name(out_dir, group[0])
                        bg_vol = float(self.bgm_volume_var.get())
                        if bg_audio and os.path.isfile(bg_audio) and bg_vol > 0:
                            tmp = mix_audio_with_bgm_ffmpeg(
                                temp, bg_audio, out_dir,
                                bgm_volume=self.bgm_volume_var.get(),
                                video_volume=self.main_video_volume_var.get()
                            )
                            # đổi tên file mix ra thành desired
                            if os.path.abspath(tmp) != os.path.abspath(desired):
                                shutil.move(tmp, desired)
                            output = desired
                        else:
                            output = desired
                            shutil.copy2(temp, output)
                        
                        used_this_run.update(os.path.abspath(p) for p in group)
                    
                    elif mode == "Concat with outro music":
                        outro_mode = self.outro_mode_var.get()
                        if outro_mode == "By time limit":
                            folder = self.input_folder.get()
                            all_videos = list_all_mp4_files(folder)
                            pool = [v for v in all_videos if os.path.abspath(v) not in (used_global | used_this_run)]
                            target_seconds = float(self.time_limit_min_var.get()) * 60.0 + float(self.time_limit_sec_var.get())
                            group = pick_videos_for_time_limit(pool, target_seconds)
                            if not group:
                                self.after(0, lambda: self._append_log("Hết clip phù hợp cho Outro Time Limit."))
                                break

                        self._encode_group_to_temp(group, temp)
                        bg_audio = random.choice(self.mp3_list) if self.mp3_list else None
                        desired = get_first_vids_name(out_dir, group[0]) 
                        bg_vol = float(self.bgm_volume_var.get())
                        if bg_audio and os.path.isfile(bg_audio) and bg_vol > 0:
                            tmp = mix_audio_at_end_ffmpeg(
                                temp, bg_audio, out_dir, self.outro_duration_var.get(),
                                bgm_volume=self.bgm_volume_var.get(),
                                outro_volume=self.video_volume_var.get(),
                                video_volume=self.main_video_volume_var.get()
                            )
                            if os.path.abspath(tmp) != os.path.abspath(desired):
                                shutil.move(tmp, desired)
                            output = desired
                        else:
                            output = desired
                            shutil.copy2(temp, output)

                        used_this_run.update(os.path.abspath(p) for p in group)

                    elif mode == "Normal concat (no music)":
                        self._encode_group_to_temp(group, temp)
                        output = get_first_vids_name(out_dir, group[0])
                        shutil.copy2(temp, output)

                        used_this_run.update(os.path.abspath(p) for p in group)

                    elif mode == "Concat and Reverse":
                        trim_specs = self._build_trim_specs(group)
                        base = concat_reverse(
                            group, out_dir,
                            width=int(self.resolution_var.get().split("x")[0]),
                            height=int(self.resolution_var.get().split("x")[1]),
                            fps=self.fps_var.get(),
                            use_nvenc=self.use_nvenc_var.get(),
                            cq=self.cq_var.get(),
                            v_bitrate=self.v_bitrate_var.get(),
                            a_bitrate=self.a_bitrate_var.get(),
                            preset=self.nvenc_preset_var.get(),
                            speed_reverse=3.0,
                            trim_specs=trim_specs
                        )

                        bg_audio = random.choice(self.mp3_list) if self.mp3_list else None
                        desired = get_first_vids_name(out_dir, group[0])
                        if bg_audio and os.path.isfile(bg_audio):
                            tmp = mix_audio_with_bgm_ffmpeg(
                                base, bg_audio, out_dir,
                                bgm_volume=self.bgm_volume_var.get(),
                                video_volume=self.main_video_volume_var.get()
                            )
                            try: os.remove(base)
                            except: pass
                            if os.path.abspath(tmp) != os.path.abspath(desired):
                                shutil.move(tmp, desired)
                            output = desired
                        else:
                            shutil.move(base, desired)
                            output = desired

                    elif mode in ("Concat with time limit", "Tuan Seo Custom"):
                        folder = self.input_folder.get()
                        all_videos = list_all_mp4_files(folder)
                        if mode == "Tuan Seo Custom":
                            all_videos = [
                                v for v in all_videos
                                if os.path.basename(os.path.dirname(v)).lower() != "ok"
                            ]
                        # 1) Bỏ video đã dùng
                        pool = [v for v in all_videos if os.path.abspath(v) not in (used_global | used_this_run)]
                        # 2) Chọn group theo time-limit
                        target_seconds = float(self.time_limit_min_var.get()) * 60.0 + float(self.time_limit_sec_var.get())
                        group = pick_videos_for_time_limit(pool, target_seconds)
                        if not group:
                            msg = "Hết clip phù hợp cho Tuan Seo Custom." if mode == "Tuan Seo Custom" \
                                else "Hết clip phù hợp cho Time Limit."
                            self.after(0, lambda: self._append_log(msg))
                            break
                        # 3) Encode tạm
                        self._encode_group_to_temp(group, temp)
                        # 4) Mix BGM
                        bg_audio = random.choice(self.mp3_list) if self.mp3_list else None
                        desired = get_first_vids_name(out_dir, group[0])
                        bg_vol = float(self.bgm_volume_var.get())
                        if bg_audio and os.path.isfile(bg_audio) and bg_vol > 0:
                            tmp = mix_audio_with_bgm_ffmpeg(
                                temp, bg_audio, out_dir,
                                bgm_volume=self.bgm_volume_var.get(),
                                video_volume=self.main_video_volume_var.get()
                            )
                            if os.path.abspath(tmp) != os.path.abspath(desired):
                                shutil.move(tmp, desired)
                            output = desired
                        else:
                            output = desired
                            shutil.copy2(temp, output)
                        # 5) Đánh dấu đã dùng
                        used_this_run.update(os.path.abspath(p) for p in group)

                    elif mode == "Loop":
                        folder = self.input_folder.get()
                        all_videos = list_all_mp4_files(folder)
                        # chỉ lấy clip chưa dùng (log cũ + phiên hiện tại)
                        pool = [v for v in all_videos if os.path.abspath(v) not in (used_global | used_this_run)]

                        # chọn đúng 1 video
                        if not pool:
                            self.after(0, lambda: self._append_log("Hết clip phù hợp cho Loop mode."))
                            self._enqueue(self._job_progress_stop)
                            break
    

                        one_video = random.choice(pool)
                        group = [one_video]
                        trim_specs = self._build_trim_specs(group)
                        trim_start = trim_specs[0][0] if trim_specs and trim_specs[0] else None
                        trim_duration = trim_specs[0][1] if trim_specs and trim_specs[0] else None

                        # thời lượng mục tiêu (nếu = 0 thì chỉ copy y như cũ)
                        target_seconds = float(self.time_limit_min_var.get()) * 60.0 + float(self.time_limit_sec_var.get())
                        desired = get_first_vids_name(out_dir, one_video)

                        def _cb(p):
                            self._enqueue(lambda: self._job_progress_update(p))
                        try:
                            if target_seconds > 0:
                                # LẶP đúng 1 video duy nhất tới thời lượng mục tiêu
                                self._loop_video_to_duration(
                                    src=one_video,
                                    dst=desired,
                                    target_seconds=target_seconds,
                                    trim_start=trim_start,
                                    trim_duration=trim_duration,
                                    progress_cb=_cb
                                )
                            else:
                                # Không set time limit -> copy nguyên bản
                                if trim_start or trim_duration:
                                    self._loop_video_to_duration(
                                        src=one_video,
                                        dst=desired,
                                        target_seconds=float(trim_duration or 0),
                                        trim_start=trim_start,
                                        trim_duration=trim_duration,
                                        progress_cb=_cb
                                    )
                                else:
                                    shutil.copy2(one_video, desired)

                            output = desired
                            used_this_run.update(os.path.abspath(p) for p in group)

                        except Exception as e:
                            # fallback copy nếu lặp lỗi
                            try:
                                shutil.copy2(one_video, desired)
                                output = desired
                                used_this_run.update(os.path.abspath(p) for p in group)
                            except Exception:
                                raise e


                    log_entry = {
                        "output": os.path.abspath(output),
                        "inputs": [os.path.abspath(p) for p in group],
                        "mode": mode
                    }
                    if mode in ("Concat with time limit", "Loop"):
                        log_entry["time_limit_min"] = int(self.time_limit_min_var.get() or 0)
                        log_entry["time_limit_sec"] = int(self.time_limit_sec_var.get() or 0)
                    f_log.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                    self.after(0, lambda path=output: self.last_output_var.set(path))
                    self.after(0, lambda path=output: self._append_log(f"Đã ghép xong: {path}"))
                    if mode == "Loop":
                        self._enqueue(self._job_progress_done)

                except Exception as e:
                    log_entry = {"error": str(e), "inputs": [os.path.abspath(p) for p in group]}
                    f_log.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                finally:
                    time.sleep(0.5)
                    if os.path.exists(temp):
                        safe_remove(temp)

                f_log.flush()
                elapsed = time.time() - start_group_time
                self.elapsed_times.append(elapsed)
                self._enqueue(self._update_progress)

    def _update_progress(self):
        self.progress['value'] += 1
        done = self.progress['value']
        total = self.progress['maximum']
        remaining = max(total - done, 0)

        # cập nhật số nhóm còn lại
        self.num_groups.set(str(remaining))
        self.groups_done.set(str(done))

        percent = (done / total) * 100
        avg_time = sum(self.elapsed_times) / len(self.elapsed_times) if self.elapsed_times else 0
        eta_seconds = avg_time * remaining
        elapsed_total = time.time() - self.start_time if self.start_time else 0

        def fmt_time(t):
            m, s = divmod(int(t), 60)
            return f"{m}m{s}s" if m else f"{s}s"

        eta_str = fmt_time(eta_seconds)
        elapsed_str = fmt_time(elapsed_total)
        avg_str = f"{avg_time:.1f}s/nhóm" if avg_time else "--"
        log_text = f"[Tiến trình] {percent:.1f}% | Còn lại: {eta_str} | Đã chạy: {elapsed_str} | TB: {avg_str}"
        self.progress_infor_var.set(log_text)

    ####second progress bar for job####
    def _job_progress_start(self, i=None, total=None):
        self.progress_job.configure(mode="determinate", maximum=100, value=0)
        self.job_info_var.set(f"Đang xử lý job {i}/{total}…" if (i and total) else "Đang xử lý job…")
        self.progress_job.grid()
        self.lbl_job_info.grid()

    def _job_progress_update(self, percent: float):
        # clamp và cập nhật label
        p = 0.0 if percent is None else max(0.0, min(100.0, float(percent)))
        self.progress_job.configure(value=p)
        self.job_info_var.set(f"Đang xử lý: {p:.0f}%")

    def _job_progress_done(self, text="Xong 1 job ✓"):
        self.progress_job.configure(value=100)
        self.job_info_var.set(text)
        self.after(300, lambda: self.progress_job.configure(value=0))

    def _job_progress_stop(self):
        self.progress_job.configure(value=0)
        self.job_info_var.set("")

    def _on_done(self):
        self.btn_concat.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.status_var.set("Hoàn thành" if not self.stop_flag.is_set() else "Đã dừng")
        self.progress_infor_var.set("" if not self.stop_flag.is_set() else "Đã dừng")

        self.progress_job.configure(value=0)
        self.job_info_var.set("")
        self.reload_groups()

    def _poll_worker(self):
        if self.worker and self.worker.is_alive():
            self.after(500, self._poll_worker)
        else:
            self._on_done()

    def _enqueue(self, fn):
        self.after(0, fn)

    def open_output_folder(self):
        path = self.save_folder.get()
        if path and os.path.isdir(path):
            os.startfile(path)

    def clear_log(self):
        log_dir = os.path.abspath("log")
        ch = self.selected_channel.get().strip() or 'default'
        log_path = os.path.join(log_dir, f"{ch}.txt")
        if not os.path.exists(log_path):
            messagebox.showinfo("Xóa log", "Không có file log để xóa.")
            return
        confirm = messagebox.askyesno("Xóa log", "Bạn có chắc muốn xóa toàn bộ dữ liệu log?")
        if confirm:
            try:
                os.remove(log_path)
                messagebox.showinfo("Xóa log", "Đã xóa dữ liệu log.")
                self.reload_groups()
            except Exception as e:
                messagebox.showerror("Xóa log", f"Lỗi khi xóa log: {e}")

    def _on_group_size_change(self, event=None):
        try:
            gsize = int(self.combo_group_size.get())
            self.group_size_var.set(gsize)
            self.reload_groups()
            self.save_channel_config(force=True)
        except ValueError:
            pass

    def _list_channels(self):
        files = [f[:-5] for f in os.listdir(CONFIG_DIR) if f.endswith(".json")]
        return sorted(files) if files else []

    def _open_video_path(self, path: str):
        if os.path.exists(path):
            try:
                os.startfile(path)
            except Exception as e:
                messagebox.showerror("Lỗi mở video", f"Không thể mở:\n{path}\n\n{e}")
        else:
            messagebox.showwarning("Không tìm thấy", f"File không tồn tại:\n{path}")

    def _on_channel_change(self, event=None):
        ch = self.selected_channel.get()
        if ch:
            self.load_channel_config(ch)
            self.save_last_channel(ch)
            self.save_channel_config(force=True)

    def load_last_channel(self):
        if os.path.exists(LAST_CHANNEL_FILE):
            with open(LAST_CHANNEL_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            last = cfg.get("last_channel", "")
            if last and os.path.exists(os.path.join(CONFIG_DIR, f"{last}.json")):
                self.selected_channel.set(last)
                self.combo_channel["values"] = self._list_channels()
                self.load_channel_config(last)
                if self.bgm_folder.get() and os.path.isdir(self.bgm_folder.get()):
                    self.mp3_list = list_all_mp3_files(self.bgm_folder.get())

    def save_last_channel(self, name=None):
        cfg = {"last_channel": name or self.selected_channel.get()}
        with open(LAST_CHANNEL_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    def load_channel_config(self, name):
        path = os.path.join(CONFIG_DIR, f"{name}.json")
        if not os.path.exists(path):
            return
        try:
            self._loading = True
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)

            self.input_folder.set(cfg.get("input_folder", ""))
            self.save_folder.set(cfg.get("save_folder", ""))
            self.bgm_folder.set(cfg.get("bgm_folder", ""))
            group_size = cfg.get("group_size")
            if group_size is None or group_size < 1:
                group_size = 1
            self.group_size_var.set(group_size)
            self.bgm_volume_var.set(cfg.get("bgm_volume", 0.5))
            self.limit_videos_var.set(cfg.get("limit_videos", 0))
            #đồng bộ hiển thị
            lv = self.limit_videos_var.get()
            self.combo_limit_videos.set("All" if lv == 0 else str(lv))
            self.concat_mode.set(cfg.get('concat_mode','Concat with music background'))
            self.combo_mode.set(self.concat_mode.get())
            if self.concat_mode.get() == "Concat with outro music":
                self.video_volume_var.set(cfg.get("video_volume", 0.2))
                
            else:
                self.video_volume_var.set(0.2)
            self.main_video_volume_var.set(cfg.get("main_video_volume", 1.0))
            vs = cfg.get("video_settings", {})
            self.resolution_var.set(vs.get("resolution", "1080x1920"))
            self.fps_var.set(vs.get("fps", 60))
            self.use_nvenc_var.set(vs.get("use_nvenc", True))
            self.cq_var.set(vs.get("cq", 23))
            self.v_bitrate_var.set(vs.get("v_bitrate", "12M"))
            self.a_bitrate_var.set(vs.get("a_bitrate", "160k"))
            self.nvenc_preset_var.set(vs.get("nvenc_preset", "p4"))
            self.time_limit_min_var.set(str(vs.get("time_limit_min", 0)))
            self.time_limit_sec_var.set(str(vs.get("time_limit_sec", 0)))
            self.outro_mode_var.set(cfg.get('outro_mode', 'By group count'))
            self.combo_outro_mode.set(self.outro_mode_var.get())
            self.outro_duration_var.set(int(cfg.get("outro_duration",15)))
            odv = self.outro_duration_var.get()
            if str(odv) not in [str(v) for v in self.cbo_outro_dur["values"]]:
                self.cbo_outro_dur["values"] = [odv] + list(self.cbo_outro_dur["values"])

            self.cut_scope_var.set(cfg.get("cut_scope", "first"))
            frame_first = self._safe_int(cfg.get("cut_frame_first", 0))
            frame_last = self._safe_int(cfg.get("cut_frame_last", cfg.get("cut_frame_all", 0)))
            self.cut_frame_first_var.set(str(frame_first))
            self.cut_frame_last_var.set(str(frame_last))

            self._update_mode_visibility()


        except Exception as e:
            messagebox.showerror("Load config", f"Lỗi đọc {path}: {e}")
        
        finally:
            self._loading = False
        
        if self.bgm_folder.get() and os.path.isdir(self.bgm_folder.get()):
            try:
                self.mp3_list = list_all_mp3_files(self.bgm_folder.get())
                print(f"[INFO] Loaded {len(self.mp3_list)} mp3 files from {self.bgm_folder.get()}")
            except Exception as e:
                print(f"[WARN] Could not read mp3 folder: {e}")

        self._update_mode_visibility()

    def save_channel_config(self, force: bool = False):
        if getattr(self, "_loading", False) and not force:
            return
        ch = self.selected_channel.get()
        if not ch:
            return messagebox.showwarning("Chưa chọn channel", "Hãy chọn hoặc tạo channel trước.")
        path = os.path.join(CONFIG_DIR, f"{ch}.json")
        cfg = {
            "input_folder": self.input_folder.get(),
            "save_folder": self.save_folder.get(),
            "bgm_folder": self.bgm_folder.get(),
            "group_size": self.group_size_var.get(),
            "bgm_volume": self.bgm_volume_var.get(),
            "limit_videos": self.limit_videos_var.get(),
            "concat_mode": self.concat_mode.get(),
            "main_video_volume": self.main_video_volume_var.get(),
            "video_volume": self.video_volume_var.get(),
            "outro_mode": self.outro_mode_var.get(),
            "outro_duration": int(self.outro_duration_var.get() or 15),
            "cut_scope": self.cut_scope_var.get(),
            "cut_frame_first": self._safe_int(self.cut_frame_first_var.get()),
            "cut_frame_last": self._safe_int(self.cut_frame_last_var.get()),
            "video_settings": {
                "resolution": self.resolution_var.get(),
                "fps": self.fps_var.get(),
                "use_nvenc": self.use_nvenc_var.get(),
                "cq": self.cq_var.get(),
                "v_bitrate": self.v_bitrate_var.get(),
                "a_bitrate": self.a_bitrate_var.get(),
                "nvenc_preset": self.nvenc_preset_var.get(),
                "time_limit_min": int(self.time_limit_min_var.get() or 0),
                "time_limit_sec": int(self.time_limit_sec_var.get() or 0),   
            }
        }
        # Chỉ lưu video_volume khi đang ở chế độ outro
        if self.concat_mode.get() == "Concat with outro music":
            cfg["video_volume"] = self.video_volume_var.get()
            
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)

    def _create_channel_from_entry(self, event=None):
        name = self.entry_new_channel.get().strip()
        if not name:
            return
        path = os.path.join(CONFIG_DIR, f"{name}.json")
        if os.path.exists(path):
            messagebox.showwarning("Duplicated", f"Channel '{name}' đã tồn tại!")
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2, ensure_ascii=False)
            self.combo_channel["values"] = self._list_channels()
            self.selected_channel.set(name)
            self.load_channel_config(name)
            self.save_last_channel(name)
            self.save_channel_config(force=True)
            messagebox.showinfo("Thành công", f"Đã tạo channel mới: {name}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể tạo channel '{name}': {e}")
        finally:
            self.entry_new_channel.delete(0, 'end')

    def _add_right_click_menu(self, widget, menu_items: list[tuple[str, callable]]):
        menu = tk.Menu(self.winfo_toplevel(), tearoff=0)
        for label, command in menu_items:
            menu.add_command(label=label, command=command)

        def show_menu(event=None):
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        # Hiện menu khi bấm chuột phải
        widget.bind("<Button-3>", show_menu)
        try:
            for child in widget.winfo_children():
                child.bind("<Button-3>", show_menu)
        except Exception:
            pass

    def _clear_channel_selection(self):
        ch = self.selected_channel.get().strip()
        if not ch:
            return messagebox.showwarning("Chưa chọn", "Chưa chọn channel để xoá.")

        confirm = messagebox.askyesno("Xác nhận xoá", f"Xoá channel '{ch}' khỏi danh sách?")
        if not confirm:
            return

        # Xoá file JSON của channel
        path = os.path.join(CONFIG_DIR, f"{ch}.json")
        if os.path.exists(path):
            os.remove(path)

        # Lấy lại danh sách channel còn lại
        channels = self._list_channels()
        if channels:
            next_ch = channels[0]
            self.selected_channel.set(next_ch)
            self.combo_channel["values"] = channels
            self.load_channel_config(next_ch)
            self.save_last_channel(next_ch)
        else:
            # Không còn channel nào
            self.selected_channel.set("")
            self.combo_channel["values"] = []
            messagebox.showinfo("Đã xoá", f"Đã xoá '{ch}'. Hiện không còn channel nào.")

    def _on_global_delete(self, event=None):
        if self.selected_channel.get():
            self._clear_channel_selection()
        widget = self.focus_get()
        if isinstance(widget, ttk.Entry):
            widget.delete(0, "end")

    def _update_mode_visibility(self):
        mode = self.concat_mode.get()

        # Mặc định hiển thị BGM volume (trừ "Normal no music")
        self.lbl_bgm_text.grid()
        self.slider_volume.grid()
        self.lbl_volume.grid()

        # Time limit controls
        if (
                mode == "Concat with time limit"
                or (mode == "Concat with outro music" and self.outro_mode_var.get() == "By time limit")
                or mode == "Loop"
                or mode == 'Tuan Seo Custom'
            ):
            self._show_time_limit(True)
            self._show_group_size(False)  # không dùng group size
        else:
            self._show_time_limit(False)
            # Reverse ép group size = 1, còn lại hiện bình thường
            if mode == "Concat and Reverse":
                self.group_size_var.set(1)
                self.combo_group_size.set("1")
                self.reload_groups()
                self._show_group_size(False)
            else:
                self._show_group_size(True)

        # Outro volume
        if mode == "Concat with outro music":
            self.lbl_video_vol.grid()
            self.slider_video_vol.grid()
            self.lbl_video_vol_value.grid()
            self.lbl_outro_mode.grid()
            self.combo_outro_mode.grid()
            self.lbl_outro_dur.grid()
            self.cbo_outro_dur.grid()
        else:
            self.lbl_video_vol.grid_remove()
            self.slider_video_vol.grid_remove()
            self.lbl_video_vol_value.grid_remove()
            self.lbl_outro_mode.grid_remove()
            self.combo_outro_mode.grid_remove()
            self.lbl_outro_dur.grid_remove()
            self.cbo_outro_dur.grid_remove()

        # Normal concat: ẩn BGM + Music Folder, dời Main Video Volume lên hàng 0
        if mode in ("Normal concat (no music)", "Loop"): 
            self.lbl_bgm_text.grid_remove()
            self.slider_volume.grid_remove()
            self.lbl_volume.grid_remove()
            for w in self.music_widgets:
                w.grid_remove()
            self.lbl_main_video_vol.grid_configure(row=0, column=4, sticky="e", padx=5)
            self.slider_main_video_vol.grid_configure(row=0, column=5, sticky="ew", padx=5)
            self.lbl_main_video_vol_value.grid_configure(row=0, column=6, sticky="w", padx=5)
        else:
            for w in self.music_widgets:
                w.grid()
            self.lbl_main_video_vol.grid_configure(row=2, column=4, sticky="e", padx=5)
            self.slider_main_video_vol.grid_configure(row=2, column=5, sticky="ew", padx=5)
            self.lbl_main_video_vol_value.grid_configure(row=2, column=6, sticky="w", padx=5)

        if mode == "Loop":
            self.progress_job.grid()
            self.lbl_job_info.grid()
        else:
            self.progress_job.grid_remove()
            self.lbl_job_info.grid_remove()
    
    def _show_time_limit(self, visible=True):
        widgets = [self.lbl_time_limit, self.combo_time_limit, self.combo_time_limit_sec]
        for w in widgets:
            w.grid() if visible else w.grid_remove()

    def _toggle_advanced(self):
        self._advanced = not self._advanced

        if self._advanced:
            self.video_frame.grid()
            self.btn_advanced.configure(text="Advanced ▾", style="Advanced.On.TButton")
        else:
            self.video_frame.grid_remove()
            self.btn_advanced.configure(text="Advanced ▸", style="Advanced.TButton")

    def _toggle_nvenc(self):
        self.use_nvenc_var.set(not self.use_nvenc_var.get())

    def _update_nvenc_button(self, *args):
        if self.use_nvenc_var.get():
            self.btn_nvenc.config(text="NVENC ON", style="NvencOn.TButton")
        else:
            self.btn_nvenc.config(text="NVENC OFF", style="NvencOff.TButton")


    def _show_group_size(self, visible=True):
        widgets = [self.lbl_group_size, self.combo_group_size]
        for w in widgets:
            w.grid() if visible else w.grid_remove()

    def _update_video_volume_label(self, *args):
        val = self.video_volume_var.get()
        self.lbl_video_vol_value.config(text=f"{val * 100:.0f}%")
        self.save_channel_config()

    def _update_main_video_volume_label(self, *args):
        val = self.main_video_volume_var.get()
        self.lbl_main_video_vol_value.config(text=f"{val * 100:.0f}%")
        self.save_channel_config()

    def _build_pretty_checkbox(self, parent, text, var, command=None):
        frame = ttk.Frame(parent)
        canvas = tk.Canvas(frame, width=18, height=18, highlightthickness=0, bd=0)
        canvas.pack(side=tk.LEFT)
        label = ttk.Label(frame, text=text, font=("Trebuchet MS", 10))
        label.pack(side=tk.LEFT, padx=(6, 0))

        def draw():
            canvas.delete("all")
            checked = bool(var.get())
            fill = "#2AA50F" if checked else "#FFFFFF"
            border = "#1F7A0B" if checked else "#9AA0A6"
            canvas.create_oval(1, 1, 17, 17, fill=fill, outline=border)
            if checked:
                canvas.create_oval(6, 6, 12, 12, fill="#FFFFFF", outline="#FFFFFF")

        def toggle():
            var.set(not var.get())
            if command:
                command()

        canvas.bind("<Button-1>", lambda e: toggle())
        label.bind("<Button-1>", lambda e: toggle())
        frame.bind("<Button-1>", lambda e: toggle())
        var.trace_add("write", lambda *_: draw())
        draw()
        return frame

    def _safe_int(self, v, default=0):
        try:
            s = str(v).strip()
            return int(s) if s else default
        except Exception:
            return default

    def _on_cut_scope_change(self):
        if getattr(self, "_loading", False):
            return
        self.save_channel_config()

    def _get_cut_settings(self):
        frame_first = self._safe_int(self.cut_frame_first_var.get())
        frame_last = self._safe_int(self.cut_frame_last_var.get())
        scope = self.cut_scope_var.get()
        has_cut = bool(frame_first > 0 or frame_last > 0)
        return has_cut, scope, frame_first, frame_last

    def _build_trim_specs(self, videos: list[str]):
        has_cut, scope, frame_first, frame_last = self._get_cut_settings()
        if not has_cut:
            return None

        fps = int(self.fps_var.get() or 0)
        fps = fps if fps > 0 else 1

        specs = []
        for i, path in enumerate(videos):
            if scope == "first" and i != 0:
                specs.append(None)
                continue
            start_frames = frame_first
            end_frames = frame_last
            if start_frames <= 0 and end_frames <= 0:
                specs.append(None)
                continue

            start_cut = (start_frames / fps) if start_frames > 0 else 0.0
            end_cut = (end_frames / fps) if end_frames > 0 else 0.0
            if start_cut <= 0 and end_cut <= 0:
                specs.append(None)
                continue

            dur = get_video_duration(path)
            if dur <= 0:
                specs.append(None)
                continue
            trim_dur = dur - start_cut - end_cut
            if trim_dur <= 0.05:
                specs.append(None)
                continue

            specs.append((start_cut, trim_dur))

        return specs if any(specs) else None

    def _get_used_videos_from_log(self) -> set[str]:
        ch = self.selected_channel.get().strip() or "default"
        return get_used_videos_from_log(ch)
    
    def _loop_video_to_duration(
        self,
        src: str,
        dst: str,
        target_seconds: float,
        trim_start: float | None = None,
        trim_duration: float | None = None,
        progress_cb=None
    ):
        loop_video_to_duration(
            src=src,
            dst=dst,
            target_seconds=target_seconds,
            vol=float(self.main_video_volume_var.get()),
            use_nvenc=self.use_nvenc_var.get(),
            nvenc_preset=self.nvenc_preset_var.get(),
            cq=int(self.cq_var.get()),
            v_bitrate=self.v_bitrate_var.get(),
            fps=int(self.fps_var.get()),
            a_bitrate=self.a_bitrate_var.get(),
            trim_start=trim_start,
            trim_duration=trim_duration,
            on_progress=progress_cb
        )    
    
    def _on_time_limit_var_changed(self, *_):
        if getattr(self, "_loading", False):
            return
        self.save_channel_config()
        self.reload_groups()
