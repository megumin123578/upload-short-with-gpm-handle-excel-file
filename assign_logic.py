from imports import *


class AssignLogicMixin:
    def _schedule_preview(self):
        if hasattr(self, "_preview_job"):
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(500, self._preview)

    def _bind_text_preview(self):
        def on_change(event):
            event.widget.edit_modified(False)
            self._schedule_preview()
        self.txt_titles.bind("<<Modified>>", on_change)
        self.txt_descs.bind("<<Modified>>", on_change)
        self.txt_texts.bind("<<Modified>>", on_change)
        self.txt_times.bind("<<Modified>>", on_change)
        self.txt_dates.bind("<<Modified>>", on_change)

    def _preview(self):
        group_file = self.group_file_var.get().strip()
        if not group_file:
            messagebox.showwarning("Missing CSV", "Please select a group CSV")
            return

        titles = normalize_lines(self.txt_titles.get("1.0", tk.END))
        descs = normalize_lines(self.txt_descs.get("1.0", tk.END))
        texts = normalize_lines(self.txt_texts.get("1.0", tk.END))
        times = normalize_lines(self.txt_times.get("1.0", tk.END))
        dates = normalize_lines(self.txt_dates.get('1.0', tk.END))
        channels = self._channels_cache
        mode = self.mode_var.get()

        if not titles and not descs and not texts:
            self.tree.delete(*self.tree.get_children())
            self._last_assignments = None
            self._set_status("Inputs empty → preview cleared.")
            return

        try:
            if mode == 'channels':
                
                chosen = self.selected_profile_var.get().strip()
                if chosen:
                    # NEW: Lặp 1 channel cho MỌI dòng tiêu đề
                    n = max(len(titles), 1)
                    if n == 0:
                        self._set_status("Enter at least one title.")
                        return
                    assignments = []
                    for i in range(n):
                        t = titles[i] if i < len(titles) else (titles[0] if titles else "")
                        d = descs[i]  if i < len(descs)  else (descs[0]  if descs  else "")
                        x = texts[i]  if i < len(texts)  else (texts[0]  if texts  else "")
                        assignments.append((chosen, t, d, x))
                else:
                    # Không chọn channel cụ thể -> giữ logic cũ
                    assignments = assign_pairs(channels, titles, descs, texts, mode=mode)
            else:
                assignments = assign_pairs(channels, titles, descs, texts, mode=mode)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        key = self.group_file_var.get().strip()
        chosen_profile = self.selected_profile_var.get().strip() if self.mode_var.get() == 'channels' else None
        folder_path = self._get_mapped_folder(key, chosen_profile)


        used_paths = load_used_videos()
        session_used = set()
        self.tree.delete(*self.tree.get_children())
        extended = []
        try:
            selected_date = self.date_entry.get_date().strftime('%m/%d/%Y')
        except Exception:
            selected_date = datetime.date.today().strftime('%m/%d/%Y')

        for i, (ch, t, d, x) in enumerate(assignments):
            pt = times[i] if i < len(times) else ""
            pd = dates[i] if i < len(dates) and dates [i] else selected_date

            if folder_path and os.path.isdir(folder_path):
                directory = get_random_unused_mp4(folder_path, used_paths | session_used)
                if directory:
                    session_used.add(directory)
            else:
                directory = ""

            self.tree.insert("", tk.END, values=(ch, directory, t, d, pd, pt, x))
            extended.append((ch, directory, t, d, pd, pt, x))

        self._last_assignments = extended
        self._set_status(f"Previewed {len(assignments)} rows")

    def _save_excel(self):
        if not self._last_assignments:
            self._set_status(f"Nothing to save!!!")
            return

        def worker():
            try:
                base = os.path.splitext(self.group_file_var.get().strip())[0] or "group"
                out_name = f"{base}.xlsx"
                out_path = os.path.join(OUTPUT_DIR, out_name)

                if self.mode_var.get() == "channels":

                    def monet_for_channel(ch):
                        return "True" if settings_all.get(ch, {}).get("monetization", False) else "False"

                    group = os.path.splitext(self.group_file_var.get().strip())[0]
                    profile = self.selected_profile_var.get().strip()
                    settings_all = self._group_settings.get(group, {})

                    # Ưu tiên move_folder lưu theo profile nếu có
                    if self.mode_var.get() == "channels" and profile:
                        move_folder = settings_all.get(profile, {}).get("move_folder", "")
                    else:
                        move_folder = settings_all.get("__group__", {}).get("move_folder", "")

                    assignments = []
                    for row in self._last_assignments:
                        ch, directory, title, desc, date, time, text_val = row
                        monet = monet_for_channel(ch)

                        # Lấy tên file gốc (nếu có video)
                        file_name = os.path.basename(directory) if directory else ""
                        # Gộp thành đường dẫn đầy đủ (nếu có move_folder + file_name)
                        full_path = os.path.join(move_folder, file_name) if move_folder and file_name else move_folder

                        assignments.append((ch, directory, title, desc, date, time, full_path, monet, text_val))

                    save_assignments_to_excel(
                        assignments,
                        out_path,
                        extra_col_names=["move_folder", "monetization", "related_video"],
                    )
                else:
                    save_assignments_to_excel(
                        self._last_assignments,
                        out_path,
                        extra_col_names=["related_video"],
                    )


                self._save_group_settings()
                self._set_status(f"Saved Excel: {out_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save Excel:\n{e}")


        threading.Thread(target=worker, daemon=True).start()

    def _apply_date_time_all(self):
        if hasattr(self.date_entry, "get_date"):
            try:
                d = self.date_entry.get_date()
                date_str = d.strftime("%m/%d/%Y")
            except Exception:
                date_str = str(self.date_entry.get()).strip()
        else:
            date_str = str(self.date_entry.get()).strip()

        try:
            datetime.datetime.strptime(date_str, "%m/%d/%Y")
        except ValueError:
            messagebox.showerror("Invalid date", "Định dạng ngày phải là MM/DD/YYYY.")
            return

        hh = self.time_h_var.get().strip()
        mm = self.time_m_var.get().strip()
        step = self.step_min_var.get()

        if not (hh.isdigit() and mm.isdigit()):
            messagebox.showerror("Invalid time", "Giờ/Phút phải là số.")
            return
        h, m = int(hh), int(mm)
        if not (0 <= h <= 23 and 0 <= m <= 59):
            messagebox.showerror("Invalid time", "Giờ phải 00-23, phút 00-59.")
            return

        try:
            step = int(step)
        except Exception:
            messagebox.showerror("Invalid step", "Step (min) phải là số nguyên.")
            return

        selected_items = self.tree.selection()
        if not selected_items:
            selected_items = self.tree.get_children()

        base_dt = datetime.datetime(2000, 1, 1, h, m)

        for i, iid in enumerate(selected_items):
            tm = (base_dt + datetime.timedelta(minutes=step * i)).time()
            time_str = f"{tm.hour:02d}:{tm.minute:02d}"
            vals = list(self.tree.item(iid, "values"))
            vals += [""] * max(0, 7 - len(vals))
            ch, directory, t, desc, _, _, text_val = vals
            new_vals = (ch, directory, t, desc, date_str, time_str, text_val)
            self.tree.item(iid, values=new_vals)
            if self._last_assignments:
                try:
                    index = self.tree.index(iid)
                    if 0 <= index < len(self._last_assignments):
                        self._last_assignments[index] = new_vals
                except Exception:
                    pass

        self._set_status(f"Đã áp dụng ngày {date_str} cho {len(selected_items)} dòng được chọn.")

    def _combine_excels(self):
        input_dir = OUTPUT_DIR
        move_folder = self.move_folder_var.get().strip()
        if self.mode_var.get() == "channels":
            output_file = EXCEL_DIR_NP
        else:
            output_file = EXCEL_DIR
        try:
            count, files = combine_excels(input_dir, output_file, move_folder, get_mp4_filename)
            if count == 0:
                messagebox.showwarning("No files", f"Không tìm thấy file Excel nào trong:\n{input_dir}")
                return
            self._set_status(f"Combined {count} files → {output_file}")
            messagebox.showinfo("Done", "Combined successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi combine:\n{e}")

    def _paste_from_clipboard(self, append=True):
        # === 1) đọc clipboard ===
        try:
            raw = self.clipboard_get()
        except Exception:
            messagebox.showwarning("Clipboard", "Không đọc được clipboard (hãy copy từ Excel trước).")
            return
        text = raw.strip().replace("\r\n", "\n").replace("\r", "\n")
        rows = [r for r in text.split("\n") if r.strip()]
        if not rows:
            messagebox.showwarning("Clipboard", "Dữ liệu rỗng.")
            return
        grid = [r.split("\t") for r in rows]
        header_map = ["titles", "descs", "texts", "dates", "times"][:len(grid[0])]
        data_rows = grid
        titles, descs, texts, dates, times = [], [], [], [], []
        for row in data_rows:
            row = row + [""] * 5
            cur_title = cur_desc = cur_text = cur_date = cur_time = None
            for idx, val in enumerate(row):
                dest = header_map[idx] if idx < len(header_map) else None
                if not dest:
                    continue
                s = val.strip()
                if dest == "titles": cur_title = s
                elif dest == "descs": cur_desc = s
                elif dest == "texts": cur_text = s
                elif dest == "dates": cur_date = s
                elif dest == "times": cur_time = s
            if cur_title is not None: titles.append(cur_title)
            if cur_desc  is not None: descs.append(cur_desc)
            if cur_text  is not None: texts.append(cur_text)
            if cur_date  is not None: dates.append(cur_date)
            if cur_time  is not None: times.append(cur_time)

        # === 2) lấy anchor của vùng bôi đen (nếu có) và xóa selection ===
        def _sel_anchor(w):
            try:
                return w.index("sel.first") if w and w.tag_ranges("sel") else None
            except Exception:
                return None

        widgets = {
            "txt_titles": getattr(self, "txt_titles", None),
            "txt_descs":  getattr(self, "txt_descs",  None),
            "txt_texts":  getattr(self, "txt_texts",  None),
            "txt_dates":  getattr(self, "txt_dates",  None),
            "txt_times":  getattr(self, "txt_times",  None),
        }
        anchors = {name: _sel_anchor(w) for name, w in widgets.items()}

        # XÓA phần đang bôi đen (nếu có)
        for name, w in widgets.items():
            try:
                if w and w.tag_ranges("sel"):
                    w.delete("sel.first", "sel.last")
            except Exception:
                pass

        # === 3) helper: ghi theo anchor nếu có, không thì append như cũ ===
        def _write(txt_widget_name, lines, *, insert_at=None):
            w = widgets.get(txt_widget_name)
            if not w:
                return
            piece = "\n".join(lines) if lines else ""
            if not piece:
                return
            if insert_at is not None:
                w.insert(insert_at, piece)
            else:
                existing = w.get("1.0", "end-1c")
                if existing.strip() and not existing.endswith("\n"):
                    w.insert("end", "\n")
                w.insert("end", piece)

        # widget không có selection vẫn append bình thường.
        _write("txt_titles", titles, insert_at=anchors.get("txt_titles"))
        _write("txt_descs",  descs,  insert_at=anchors.get("txt_descs"))
        _write("txt_texts",  texts,  insert_at=anchors.get("txt_texts"))
        _write("txt_dates",  dates,  insert_at=anchors.get("txt_dates"))
        _write("txt_times",  times,  insert_at=anchors.get("txt_times"))

        replaced = any(anchors.values())
        self._set_status(
            f"{'Replaced' if replaced else 'Appended'} "
            f"{max(len(titles), len(descs), len(dates), len(times))} dòng từ Excel."
        )
        self._schedule_preview()

