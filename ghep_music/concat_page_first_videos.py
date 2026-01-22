from .helper import *


class ConcatPageFirstVideosMixin:
    def _get_first_video_rows(self) -> list[dict]:
        rows = []
        for row in self.first_video_rows:
            path = str(row.get("path", "")).strip()
            time_limit = str(row.get("time_limit", "")).strip()
            status = str(row.get("status", "")).strip()
            if path:
                rows.append({"path": path, "time_limit": time_limit, "status": status})
        return rows

    def _set_first_video_rows(self, rows: list[dict]):
        self.first_video_rows = []
        for row in rows or []:
            path = str(row.get("path", "")).strip()
            time_limit = str(row.get("time_limit", "")).strip()
            status = str(row.get("status", "")).strip() or "pending"
            if path:
                self.first_video_rows.append({"path": path, "time_limit": time_limit, "status": status})
        self._update_first_videos_button_label()

    def _update_first_videos_button_label(self):
        if hasattr(self, "btn_first_videos"):
            self.btn_first_videos.config(text="First video")

    def _status_display(self, status: str, has_path: bool = True) -> str:
        if not has_path:
            return ""
        s = (status or "").strip().lower()
        if s == "done":
            return "🟩 done"
        return "🟨 pending"

    def _status_normalize(self, value: str) -> str:
        s = (value or "").strip().lower()
        if not s:
            return ""
        if "done" in s:
            return "done"
        if "pending" in s:
            return "pending"
        return "pending"

    def _status_tag(self, status: str) -> tuple[str, ...]:
        s = (status or "").strip().lower()
        if s == "done":
            return ("done",)
        if s == "pending":
            return ("pending",)
        return ()

    def _reset_first_video_statuses(self):
        changed = False
        for row in self.first_video_rows:
            if row.get("path") and row.get("status") != "pending":
                row["status"] = "pending"
                changed = True
        if changed:
            self._update_first_videos_table()

    def _update_first_videos_table(self):
        tree = getattr(self, "_first_videos_tree", None)
        if not tree or not tree.winfo_exists():
            return
        children = list(tree.get_children())
        for idx, row in enumerate(self.first_video_rows):
            if idx >= len(children):
                break
            status = row.get("status", "pending")
            values = list(tree.item(children[idx], "values"))
            values += [""] * max(0, 3 - len(values))
            values[0] = row.get("path", "")
            values[1] = row.get("time_limit", "")
            values[2] = self._status_display(status, bool(values[0].strip()))
            tree.item(children[idx], values=values, tags=self._status_tag(status))

    def _set_first_video_status_by_group(self, group_index: int, status: str):
        row_map = getattr(self, "_first_video_row_map", [])
        if group_index < 0 or group_index >= len(row_map):
            return
        row_idx = row_map[group_index]
        if row_idx < 0 or row_idx >= len(self.first_video_rows):
            return
        self.first_video_rows[row_idx]["status"] = status
        self._update_first_videos_table()
        self.save_channel_config(force=True)

    def _set_first_video_status_by_path(self, path: str, status: str):
        if not path:
            return
        target = os.path.abspath(path).lower()
        for row in self.first_video_rows:
            row_path = os.path.abspath(row.get("path", "")).lower()
            if row_path == target:
                row["status"] = status
                self._update_first_videos_table()
                self.save_channel_config(force=True)
                return

    def _parse_time_limit_to_seconds(self, val: str):
        s = (val or "").strip()
        if not s:
            return None
        try:
            minutes = float(s)
            seconds = int(minutes * 60)
            return seconds if seconds > 0 else None
        except Exception:
            return None

    def _build_first_video_groups(self, videos: list[str], rows: list[dict], group_size: int):
        group_size = max(1, int(group_size or 1))
        if not rows:
            return []
        first_paths = [r["path"] for r in rows if r.get("path")]
        if group_size == 1:
            return [[v] for v in first_paths]

        first_set = {v.lower() for v in first_paths}
        pool = [v for v in videos if v.lower() not in first_set]
        random.shuffle(pool)

        groups = []
        row_map = []
        for row_idx, row in enumerate(rows):
            first_video = row.get("path", "")
            if not first_video:
                continue
            time_limit = self._parse_time_limit_to_seconds(row.get("time_limit", ""))
            if time_limit:
                selected = pick_videos_for_time_limit(list(pool), time_limit)
                if not selected:
                    break
                groups.append([first_video] + selected)
                row_map.append(row.get("row_index", row_idx))
                for p in selected:
                    try:
                        pool.remove(p)
                    except ValueError:
                        pass
            else:
                chunk_size = group_size - 1
                if len(pool) < chunk_size:
                    break
                chunk = pool[:chunk_size]
                groups.append([first_video] + chunk)
                row_map.append(row.get("row_index", row_idx))
                del pool[:chunk_size]

        self._first_video_row_map = row_map
        return groups

    def _open_first_videos_table(self):
        if getattr(self, "_first_videos_win", None) and self._first_videos_win.winfo_exists():
            self._first_videos_win.lift()
            return

        win = tk.Toplevel(self)
        win.title("First videos table")
        win.transient(self)
        win.grab_set()
        self._first_videos_win = win

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        frm.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("FirstVideos.Treeview", font=("Segoe UI Emoji", 10))

        tree = ttk.Treeview(
            frm,
            columns=("path", "limit", "status"),
            show="headings",
            height=10,
            style="FirstVideos.Treeview",
        )
        tree.heading("path", text="First video")
        tree.heading("limit", text="Time limit (min)")
        tree.heading("status", text="Status")
        tree.column("path", width=440, anchor="w")
        tree.column("limit", width=160, anchor="center")
        tree.column("status", width=100, anchor="center")
        tree.grid(row=0, column=0, columnspan=4, sticky="nsew")
        frm.rowconfigure(0, weight=1)

        scroll = ttk.Scrollbar(frm, orient="vertical", command=tree.yview)
        scroll.grid(row=0, column=4, sticky="ns")
        tree.configure(yscrollcommand=scroll.set)

        tree.tag_configure("pending", background="#FFF3CD", foreground="#111111")
        tree.tag_configure("done", background="#D4EDDA", foreground="#111111")

        self._first_videos_snapshot = list(self.first_video_rows)
        for row in self._get_first_video_rows():
            status = row.get("status", "pending") or "pending"
            tree.insert(
                "", "end",
                values=(row["path"], row.get("time_limit", ""), self._status_display(status, True)),
                tags=self._status_tag(status),
            )

        def _ensure_empty_rows(min_rows=20):
            existing = len(tree.get_children())
            for _ in range(max(0, min_rows - existing)):
                tree.insert("", "end", values=("", "", ""))

        _ensure_empty_rows()

        frm.columnconfigure(0, weight=1)

        def _insert_row(path: str, limit: str):
            path = path.strip()
            limit = limit.strip()
            if not path:
                return
            tree.insert(
                "", "end",
                values=(path, limit, self._status_display("pending", True)),
                tags=self._status_tag("pending"),
            )

        editor_state = {"widget": None, "row_id": None, "col_index": 0}

        def _start_edit(row_id, col_id):
            if editor_state["widget"] is not None:
                try:
                    editor_state["widget"].destroy()
                except Exception:
                    pass
                editor_state["widget"] = None

            if not row_id or not col_id:
                return
            col_index = int(col_id[1:]) - 1
            bbox = tree.bbox(row_id, col_id)
            if not bbox:
                return
            x, y, w, h = bbox
            old_values = list(tree.item(row_id, "values"))
            old_text = old_values[col_index] if col_index < len(old_values) else ""

            if col_index == 2:
                has_path = bool(old_values[0].strip()) if old_values else False
                if not has_path:
                    return
                cur = self._status_normalize(old_text) or "pending"
                new_status = "done" if cur == "pending" else "pending"
                values = list(tree.item(row_id, "values"))
                values += [""] * max(0, 3 - len(values))
                values[2] = self._status_display(new_status, True)
                tree.item(row_id, values=values, tags=self._status_tag(new_status))
                try:
                    children = list(tree.get_children())
                    row_idx = children.index(row_id)
                    if 0 <= row_idx < len(self.first_video_rows):
                        self.first_video_rows[row_idx]["status"] = new_status
                        self._first_videos_snapshot = list(self.first_video_rows)
                        self.save_channel_config(force=True)
                except Exception:
                    pass
                return
            editor = ttk.Entry(tree)
            editor_state["widget"] = editor
            editor.place(x=x, y=y, width=w, height=h)
            editor.insert(0, old_text)
            editor.focus_set()
            editor.select_range(0, tk.END)

            def _commit(save: bool):
                new_text = editor.get().strip() if save else old_text
                editor.destroy()
                editor_state["widget"] = None
                values = list(tree.item(row_id, "values"))
                values += [""] * max(0, 3 - len(values))
                values[col_index] = new_text
                has_path = bool(values[0].strip())
                if col_index == 2:
                    normalized = self._status_normalize(new_text)
                    values[2] = self._status_display(normalized, has_path) if has_path else ""
                    tree.item(row_id, values=values, tags=self._status_tag(normalized))
                elif col_index == 0 and not has_path:
                    values[2] = ""
                    tree.item(row_id, values=values, tags=())
                elif col_index in (0, 1) and has_path and not values[2].strip():
                    values[2] = self._status_display("pending", True)
                    tree.item(row_id, values=values, tags=self._status_tag("pending"))
                else:
                    tree.item(row_id, values=values)
                # keep edits in table only

            editor.bind("<Return>", lambda e: _commit(True))
            editor.bind("<Escape>", lambda e: _commit(False))
            editor.bind("<FocusOut>", lambda e: _commit(True))
            editor.bind("<Control-v>", lambda e: (_commit(True), _on_paste(e), "break"))

        def _on_single_click(event):
            row_id = tree.identify_row(event.y)
            col_id = tree.identify_column(event.x)
            if not row_id or col_id not in ("#1", "#2", "#3"):
                return
            tree.selection_set(row_id)
            tree.focus(row_id)
            editor_state["row_id"] = row_id
            editor_state["col_index"] = int(col_id[1:]) - 1
            _start_edit(row_id, col_id)

        def _on_paste(event=None):
            try:
                data = win.clipboard_get()
            except Exception:
                return "break"
            if not data:
                return "break"
            if editor_state["widget"] is not None:
                try:
                    editor_state["widget"].destroy()
                except Exception:
                    pass
                editor_state["widget"] = None
            rows = [line.split("\t") for line in data.splitlines()]
            if not rows:
                return "break"

            children = list(tree.get_children())
            start_row_idx = 0
            start_col_idx = 0
            if editor_state["row_id"] in children:
                start_row_idx = children.index(editor_state["row_id"])
            start_col_idx = editor_state.get("col_index", 0) or 0

            max_needed = start_row_idx + len(rows)
            while len(children) < max_needed:
                tree.insert("", "end", values=("", "", ""))
                children = list(tree.get_children())

            for r_idx, cols in enumerate(rows):
                if not cols:
                    continue
                row_index = start_row_idx + r_idx
                item_id = children[row_index]
                values = list(tree.item(item_id, "values"))
                values += [""] * max(0, 3 - len(values))
                for c_idx, val in enumerate(cols):
                    target_col = start_col_idx + c_idx
                    if target_col >= 2:
                        break
                    values[target_col] = val.strip()
                has_path = bool(values[0].strip())
                if has_path and not values[2].strip():
                    values[2] = self._status_display("pending", True)
                    tree.item(item_id, values=values, tags=self._status_tag("pending"))
                elif not has_path:
                    values[2] = ""
                    tree.item(item_id, values=values, tags=())
                else:
                    tree.item(item_id, values=values)
            return "break"

        def _delete_selected():
            sel = tree.selection()
            for item in sel:
                tree.delete(item)

        tree.bind("<ButtonRelease-1>", _on_single_click)
        tree.bind("<Control-v>", _on_paste)
        tree.bind("<Delete>", lambda e: _delete_selected())

        def _add_paths(paths):
            if not paths:
                return
            tree.configure(displaycolumns=())
            try:
                children = list(tree.get_children())
                start_idx = None
                for i, item_id in enumerate(children):
                    values = list(tree.item(item_id, "values"))
                    if not values or not str(values[0]).strip():
                        start_idx = i
                        break
                if start_idx is None:
                    start_idx = len(children)
                max_needed = start_idx + len(paths)
                while len(children) < max_needed:
                    tree.insert("", "end", values=("", "", ""))
                    children = list(tree.get_children())
                for offset, p in enumerate(paths):
                    item_id = children[start_idx + offset]
                    tree.item(
                        item_id,
                        values=(p, "", self._status_display("pending", True)),
                        tags=self._status_tag("pending"),
                    )
            finally:
                tree.configure(displaycolumns=("path", "limit", "status"))
                tree.update_idletasks()

        def _browse_add():
            paths = filedialog.askopenfilenames(
                title="Select first videos",
                filetypes=[("MP4 files", "*.mp4"), ("All files", "*.*")],
            )
            _add_paths(paths)

        def _parse_drop_paths(data: str) -> list[str]:
            if not data:
                return []
            parts = re.findall(r"{[^}]*}|\S+", data)
            return [p.strip("{}") for p in parts]

        try:
            from tkinterdnd2 import DND_FILES
            if hasattr(tree, "drop_target_register"):
                tree.drop_target_register(DND_FILES)
                tree.dnd_bind("<<Drop>>", lambda e: _add_paths(_parse_drop_paths(e.data)))
        except Exception:
            pass

        def on_close():
            prev = getattr(self, "_first_videos_snapshot", [])
            rows = []
            for idx, item in enumerate(tree.get_children()):
                path, limit, status = tree.item(item, "values")
                path = str(path).strip()
                limit = str(limit).strip()
                if not path:
                    continue
                status = self._status_normalize(status)
                if idx < len(prev):
                    prev_row = prev[idx]
                    prev_path = str(prev_row.get("path", "")).strip()
                    prev_limit = str(prev_row.get("time_limit", "")).strip()
                    if prev_path == path and prev_limit == limit:
                        status = prev_row.get("status", status or "pending")
                rows.append({
                    "path": path,
                    "time_limit": limit,
                    "status": status or "pending",
                })
            self._set_first_video_rows(rows)
            self.save_channel_config(force=True)
            self.reload_groups()
            self._first_videos_tree = None
            win.destroy()

        def on_clear():
            for item in tree.get_children():
                tree.delete(item)
            _ensure_empty_rows()

        def _mark_all(status: str):
            for item_id in tree.get_children():
                values = list(tree.item(item_id, "values"))
                values += [""] * max(0, 3 - len(values))
                if not str(values[0]).strip():
                    continue
                values[2] = self._status_display(status, True)
                tree.item(item_id, values=values, tags=self._status_tag(status))
            for row in self.first_video_rows:
                if row.get("path"):
                    row["status"] = status
            self._first_videos_snapshot = list(self.first_video_rows)
            self.save_channel_config(force=True)

        self._first_videos_tree = tree
        btn_row = ttk.Frame(frm)
        btn_row.grid(row=3, column=0, sticky="we", pady=(6, 0))
        btn_row.columnconfigure(0, weight=1)
        btn_left = ttk.Frame(btn_row)
        btn_left.grid(row=0, column=0, sticky="w")
        btn_right = ttk.Frame(btn_row)
        btn_right.grid(row=0, column=1, sticky="e")

        ttk.Button(btn_left, text="Browser", command=_browse_add).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_left, text="Clear", command=on_clear).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_left, text="All Pending", command=lambda: _mark_all("pending")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_left, text="All Done", command=lambda: _mark_all("done")).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btn_right, text="Save", command=on_close).pack(side=tk.RIGHT)

        def _on_win_close():
            on_close()

        win.protocol("WM_DELETE_WINDOW", _on_win_close)
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 3
        win.geometry(f"{w}x{h}+{x}+{y}")
