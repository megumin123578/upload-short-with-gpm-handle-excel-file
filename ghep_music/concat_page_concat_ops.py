from .helper import *


class ConcatPageConcatOpsMixin:
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
            "Concat with first video",
            "Normal concat (no music)",
            "Concat and Reverse",
            "Concat with outro music",   # vì mode này vẫn dùng group size khi chọn “By group count”
        }

        if mode == "Concat with first video":
            rows = self._get_first_video_rows()
            pending_rows = [r for r in rows if r.get("path") and r.get("status", "pending") != "done"]
            if not pending_rows:
                return messagebox.showwarning("No pending", "No pending first videos.")
            invalid = [r["path"] for r in pending_rows if not os.path.isfile(r["path"])]
            if invalid:
                return messagebox.showwarning("Invalid first video", f"Invalid path:\n{invalid[0]}")

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
            if mode != "Concat with first video" and limit_groups > 0:
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
                    if mode in ("Concat with music background", "Concat with first video"):
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
                    if mode == "Concat with first video":
                        self.after(0, lambda i=idx - 1: self._set_first_video_status_by_group(i, "done"))
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

