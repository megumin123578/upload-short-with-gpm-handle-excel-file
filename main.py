from imports import *
from assign_mixin import AssignMixin
from assign_logic import AssignLogicMixin
from main_ui import MainUIMixin
import random


class App(tk.Tk, AssignMixin, AssignLogicMixin, MainUIMixin):
    def __init__(self):
        super().__init__()
        style = ttk.Style()
        style.theme_use("clam")
        setup_theme(style, self)

        self._update_restarted = False

        self._active_nav_key = None

        self.title(APP_TITLE)
        self.minsize(1000, 600)

        # ====== STATE ======
        self.group_file_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="titles") 
        self.status_var = tk.StringVar(value="Ready.")
        self._channels_cache = []
        self._last_assignments = None
        self._watch_last_assignments = None
        self._watch_input_pools = None
        self._watch_state_path = os.path.join(os.path.dirname(__file__), 'watch_state.json')
        self.selected_profile_var = tk.StringVar(value="")

        self.date_entry = None
        now = datetime.datetime.now()
        self.time_h_var = tk.StringVar(value=f"{now.hour:02d}")
        self.time_m_var = tk.StringVar(value=f"{now.minute:02d}")
        self.step_min_var = tk.IntVar(value=0)

        self._monetization_vars = {}
        self.monetization_var = tk.BooleanVar(value=False)  # giá»¯ biáº¿n táº¡m thá»i cho UI

        self._group_settings = load_group_settings()
        self._restoring = False

        # ====== MENUBAR (Profiles + Help) ======
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        profiles_menu = tk.Menu(menubar, tearoff=0)
        profiles_menu.add_command(label="Manage Profiles", command=self._open_profile_manager)
        profiles_menu.add_command(label="Add Group", command=self._add_group)
        profiles_menu.add_command(label="Delete Group", command=self._delete_group)
        profiles_menu.add_command(label="Mapping Folder...", command=self._map_group_folder)
        menubar.add_cascade(label="Profiles", menu=profiles_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Check for Updates...", command=self._check_for_updates)
        help_menu.add_separator()
        def _show_about(): #show update info
            about_path = os.path.join(os.path.dirname(__file__), "update_content.txt")
            if os.path.exists(about_path):
                with open(about_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
            else:
                content = f"App version: {APP_VERSION}\n\n(update_content.txt not found)"
            messagebox.showinfo("About", content)

        help_menu.add_command(label=f"About (v{APP_VERSION})", command=_show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self._build_shell()

        # ====== PAGES ======
        self.pages = {}
        self._lazy_page_builders = {
            "concat": self._build_concat_page,
            "watch": self._build_watch_page,
        }
        self._build_assign_page()

        self.bind_all("<Control-b>", self._on_hotkey_paste) #ctrl +b to paste values from clipboard
        self.bind_all("<Control-s>", self._on_hotkey_save) #ctrl +s save to save excel
        # Hiá»ƒn thá»‹ page máº·c Ä‘á»‹nh
        self._show_page("concat")

        self.after(1, self._start_init_in_bg)
        self.after(50, self._equalize_inputs)


    def _on_app_close(self):
        try:
            if hasattr(self, "watch_rows_var"):
                self._watch_save_state()
        except Exception:
            pass
        self.destroy()
    # Shell: Sidebar + Content
    def _on_hotkey_save(self, event= None):
        self._save_excel()
        return "break" #trÃ¡nh hÃ nh vi máº·c Ä‘á»‹nh
    def _on_hotkey_paste(self, event=None):
        self._paste_from_clipboard()
        return "break"  

    def _build_assign_page(self):
        page = ttk.Frame(self._content)
        self.pages["assign"] = page

        self._build_header(parent=page)
        self._build_inputs(parent=page)
        self._build_preview(parent=page)
        self._build_footer(parent=page)

    def _build_concat_page(self):
        from ghep_music.concat_page import ConcatPage
        page = ttk.Frame(self._content)       # khung trang
        self.pages["concat"] = page
        # NhÃºng UI concat
        self.concat_page = ConcatPage(page) 
        self.concat_page.pack(fill="both", expand=True)

    def _build_watch_page(self):
        page = ttk.Frame(self._content)
        self.pages["watch"] = page
        self.watch_rows_var = tk.IntVar(value=20)

        top = ttk.Frame(page, padding=(10, 10, 10, 0))
        top.pack(fill=tk.X)
        ttk.Label(top, text="Watch").pack(side=tk.LEFT)
        ttk.Label(
            top,
            text="(uses current Group/Mode from Auto Upload)",
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(top, text="Rows:").pack(side=tk.LEFT, padx=(20, 6))
        tk.Spinbox(top, from_=1, to=10000, width=6, textvariable=self.watch_rows_var).pack(side=tk.LEFT)
        self.watch_true_count_var = tk.StringVar(value="0")
        ttk.Label(top, text="Comment/Like:").pack(side=tk.LEFT, padx=(12, 6))
        ttk.Entry(top, textvariable=self.watch_true_count_var, width=8).pack(side=tk.LEFT)
        ttk.Button(top, text="Reroll", command=self._watch_reroll).pack(side=tk.LEFT, padx=(12, 6))
        ttk.Button(top, text="Clear", command=self._watch_clear).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(top, text="Save", command=self._watch_save_excel).pack(side=tk.LEFT)

        input_wrap = ttk.Frame(page, padding=10)
        input_wrap.pack(fill=tk.BOTH, expand=True)
        paned = tk.PanedWindow(input_wrap, orient=tk.HORIZONTAL, sashrelief=tk.RAISED, sashwidth=6)
        paned.pack(fill=tk.BOTH, expand=True)

        def make_section(label_text):
            frame = ttk.Frame(paned)
            ttk.Label(frame, text=label_text).pack(anchor="w")
            txt = tk.Text(frame, height=8, wrap=tk.WORD)
            txt.pack(fill=tk.BOTH, expand=True)
            txt.bind("<Control-a>", lambda e, widget=txt: (widget.tag_add("sel", "1.0", "end-1c"), "break"))
            return frame, txt

        f1, self.watch_txt_comments = make_section("Comment pool (optional, one per line)")
        f2, self.watch_txt_channels = make_section("Channel list (one per line)")
        for fr in (f1, f2):
            paned.add(fr)

        preview_wrap = ttk.Frame(page, padding=(10, 0, 10, 10))
        preview_wrap.pack(fill=tk.BOTH, expand=True)
        cols = ("channel", "comment", "like")
        self.watch_tree = ttk.Treeview(preview_wrap, columns=cols, show="headings", height=12)
        for col in cols:
            self.watch_tree.heading(col, text=col.capitalize())
            if col == "channel":
                self.watch_tree.column(col, width=200, anchor="w")
            elif col == "comment":
                self.watch_tree.column(col, width=520, anchor="w")
            elif col == "like":
                self.watch_tree.column(col, width=120, anchor="w")
        vsb = ttk.Scrollbar(preview_wrap, orient="vertical", command=self.watch_tree.yview)
        self.watch_tree.configure(yscroll=vsb.set)
        self.watch_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        # Load saved data first to avoid trace callbacks overwriting file with empty defaults.
        self._watch_load_state()

        self.watch_rows_var.trace_add("write", lambda *_: self._watch_save_state())
        self.watch_true_count_var.trace_add("write", lambda *_: self._watch_save_state())
        for w in (self.watch_txt_comments, self.watch_txt_channels):
            w.bind("<KeyRelease>", lambda e: self._watch_save_state())
            w.bind("<FocusOut>", lambda e: self._watch_save_state())

    def _watch_get_state_path(self):
        return self._watch_state_path

    def _watch_save_state(self):
        if not hasattr(self, "watch_rows_var"):
            return
        try:
            data = {
                "rows": int(self.watch_rows_var.get() or 0),
                "true_count": str(self.watch_true_count_var.get() or "0"),
                "comments_text": self.watch_txt_comments.get("1.0", "end-1c"),
                "channels_text": self.watch_txt_channels.get("1.0", "end-1c"),
                "assignments": [list(r) for r in (self._watch_last_assignments or [])],
            }
            with open(self._watch_get_state_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _watch_load_state(self):
        path = self._watch_get_state_path()
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        rows_val = data.get("rows", 20)
        try:
            self.watch_rows_var.set(max(1, int(rows_val)))
        except Exception:
            self.watch_rows_var.set(20)
        self.watch_true_count_var.set(str(data.get("true_count", "0")))

        self.watch_txt_comments.delete("1.0", tk.END)
        self.watch_txt_comments.insert("1.0", data.get("comments_text", ""))
        self.watch_txt_channels.delete("1.0", tk.END)
        self.watch_txt_channels.insert("1.0", data.get("channels_text", ""))

        assignments = data.get("assignments") or []
        self.watch_tree.delete(*self.watch_tree.get_children())
        safe_rows = []
        for row in assignments:
            if isinstance(row, (list, tuple)) and len(row) >= 3:
                vals = (str(row[0]), str(row[1]), str(row[2]))
                self.watch_tree.insert("", tk.END, values=vals)
                safe_rows.append(vals)
        self._watch_last_assignments = safe_rows or None
    def _watch_collect_pools(self):
        comments = normalize_lines(self.watch_txt_comments.get("1.0", tk.END))
        channels = normalize_lines(self.watch_txt_channels.get("1.0", tk.END))
        count_raw = self.watch_true_count_var.get().strip()

        if not channels:
            raise ValueError("Watch: Channel list is empty.")
        try:
            if not count_raw:
                true_count = 0
            else:
                true_count = int(count_raw)
                if true_count < 0:
                    raise ValueError
        except Exception:
            raise ValueError("Watch: Comment/Like must be a non-negative integer.")
        return {
            "comments": comments or [""],
            "channels": channels,
            "true_count": true_count,

        }

    def _watch_generate_assignments(self, row_count, pools):
        value_count = max(0, int(pools["true_count"]))
        channel_csv = ",".join(pools["channels"])

        rows = []
        for _ in range(max(1, row_count)):
            comment_values = [random.choice(("true", "false")) for _ in range(value_count)]
            like_values = [random.choice(("true", "false")) for _ in range(value_count)]
            comment_csv = ",".join(comment_values)
            like_csv = ",".join(like_values)
            rows.append((channel_csv, comment_csv, like_csv))
        return rows

    def _watch_preview(self):
        try:
            row_count = int(self.watch_rows_var.get())
            if row_count <= 0:
                raise ValueError("Rows must be > 0.")
            pools = self._watch_collect_pools()
            rows = self._watch_generate_assignments(row_count, pools)
        except Exception as e:
            messagebox.showerror("Watch", str(e))
            return

        self.watch_tree.delete(*self.watch_tree.get_children())
        for row in rows:
            self.watch_tree.insert("", tk.END, values=row)

        self._watch_input_pools = pools
        self._watch_last_assignments = rows
        self._set_status(f"Watch previewed {len(rows)} rows.")

    def _watch_reroll(self):
        try:
            row_count = int(self.watch_rows_var.get())
            pools = self._watch_input_pools or self._watch_collect_pools()
            rows = self._watch_generate_assignments(row_count, pools)
        except Exception as e:
            messagebox.showerror("Watch", str(e))
            return

        self.watch_tree.delete(*self.watch_tree.get_children())
        for row in rows:
            self.watch_tree.insert("", tk.END, values=row)

        self._watch_last_assignments = rows
        self._watch_save_state()
        self._set_status(f"Watch rerolled {len(rows)} rows.")

    def _watch_clear(self):
        for w in (
            self.watch_txt_comments,
            self.watch_txt_channels,
        ):
            w.delete("1.0", tk.END)
        self.watch_tree.delete(*self.watch_tree.get_children())
        self._watch_last_assignments = None
        self._watch_input_pools = None
        self._watch_save_state()
        self._set_status("Cleared Watch inputs and preview.")

    def _watch_save_excel(self):
        if not self._watch_last_assignments:
            self._set_status("Watch: nothing to save.")
            return

        def worker():
            try:
                out_name = "auto_watch.xlsx"
                out_path = os.path.join(OUTPUT_DIR, out_name)
                from openpyxl import Workbook
                from openpyxl.styles import Font
                wb = Workbook()
                ws = wb.active
                ws.title = "Watch"
                ws.append(["channel", "comment", "like"])
                for c_idx in range(1, 4):
                    ws.cell(row=1, column=c_idx).font = Font(bold=True)
                for row in self._watch_last_assignments:
                    ws.append(list(row))
                if os.path.exists(out_path):
                    os.remove(out_path)
                wb.save(out_path)

                self._set_status(f"Watch saved Excel: {out_path}")
            except Exception as e:
                messagebox.showerror("Watch", f"Failed to save Excel:\n{e}")

        threading.Thread(target=worker, daemon=True).start()







    def _refresh_group_files(self, load_channels: bool = True):
        files = list_group_csvs(GROUPS_DIR)
        groups = [os.path.splitext(f)[0] for f in files]

        self.group_combo["values"] = groups
        cur = self.group_file_var.get()

        if not groups:
            self.group_file_var.set("")
            self.channel_count_lbl.config(text="0 channels")
            self._set_status(f"No CSV files in: {GROUPS_DIR}")
            return

        if cur not in groups:
            self.group_file_var.set(groups[0])

        if load_channels:
            self._load_channels()

    def _load_channels(self):
        name = self.group_file_var.get().strip()
        if not name:
            return

        self._restoring = True  # Báº®T Äáº¦U náº¡p

        csv_path = os.path.join(GROUPS_DIR, name + ".csv")
        channels = read_channels_from_csv(csv_path)
        self._channels_cache = channels
        self._update_profile_combo()

        settings_all = self._group_settings.get(name, {})
        meta = settings_all.get("__meta__", {}) if isinstance(settings_all, dict) else {}

        # 1) KhÃ´i phá»¥c mode
        loaded_mode = meta.get("mode")
        if loaded_mode in ("titles", "channels"):
            self.mode_var.set(loaded_mode)

        # 2) KhÃ´i phá»¥c last profile
        last_profile = meta.get("last_profile", "")
        if last_profile and (last_profile in self._channels_cache):
            self.selected_profile_var.set(last_profile)
        else:
            if self.mode_var.get() == "channels" and self._channels_cache:
                for ch in self._channels_cache:
                    if ch in settings_all:
                        self.selected_profile_var.set(ch)
                        break
                else:
                    self.selected_profile_var.set(self._channels_cache[0])

        # 3) Náº P monetization CHO PROFILE ÄÃƒ CHá»ŒN (TRÆ¯á»šC khi gá»i _on_mode_change)
        profile = self.selected_profile_var.get().strip()
        if profile:
            monet = settings_all.get(profile, {}).get("monetization", False)
            self._monetization_vars[profile] = monet
            self.monetization_var.set(monet)
        else:
            self.monetization_var.set(False)

        # 4) Render UI theo mode/profile (khÃ´ng cho phÃ©p lÆ°u trong lÃºc restoring)
        self._on_mode_change()

        self._refresh_channel_stats_label()

        mapped_dir = self._get_mapped_folder(name, self.selected_profile_var.get().strip())
        mapped_note = f" | mapped: {mapped_dir or '(none)'}"
        self._set_status(f"Loaded {len(channels)} channels from {name}{mapped_note}")
        
        # --- KhÃ´i phá»¥c Save to ---
        profile = self.selected_profile_var.get().strip()
        settings_all = self._group_settings.get(name, {})

        if self.mode_var.get() == "channels" and profile:
            last_folder = settings_all.get(profile, {}).get("move_folder", "")
        else:
            last_folder = settings_all.get("__group__", {}).get("move_folder", "")

        # fallback: file file config cÅ©
        if not last_folder:
            last_folder = load_group_config(name) or load_group_config(name + ".csv") or ""

        self.move_folder_var.set(last_folder)
        # --- end Save to ---
        self._restoring = False  # Káº¾T THÃšC náº¡p

    def _clear_inputs(self):
        self.txt_titles.delete("1.0", tk.END)
        self.txt_descs.delete("1.0", tk.END)
        self.txt_texts.delete("1.0", tk.END)
        self.txt_dates.delete('1.0', tk.END)
        self.txt_times.delete("1.0", tk.END)
        self.tree.delete(*self.tree.get_children())
        self._last_assignments = None
        self._set_status("Cleared inputs & preview.")



    def _set_status(self, msg: str):
        self.after(0, lambda: self.status_var.set(msg))

    def _edit_row_dialog(self, item_id, index):
        vals = list(self.tree.item(item_id, "values"))
        vals += [""] * max(0, 7 - len(vals))
        ch_cur, dir_cur, title_cur, desc_cur, pd_cur, pt_cur, text_cur = vals

        win = tk.Toplevel(self)
        win.title("Edit row")
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Profile:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        ent_ch = ttk.Combobox(frm, values=[c for c in self._channels_cache], state="readonly", width=60)
        ent_ch.grid(row=0, column=1, sticky="we")
        ent_ch.set(ch_cur)

        ttk.Label(frm, text="Directory:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        ent_dir = ttk.Entry(frm, width=60)
        ent_dir.grid(row=1, column=1, sticky="we")
        ent_dir.insert(0, dir_cur)

        ttk.Label(frm, text="Title:").grid(row=2, column=0, sticky="e", padx=6, pady=4)
        ent_title = ttk.Entry(frm, width=60)
        ent_title.grid(row=2, column=1, sticky="we")
        ent_title.insert(0, title_cur)

        ttk.Label(frm, text="Description:").grid(row=3, column=0, sticky="ne", padx=6, pady=4)
        txt_desc = tk.Text(frm, width=60, height=6, wrap=tk.WORD)
        txt_desc.grid(row=3, column=1, sticky="we")
        txt_desc.insert("1.0", desc_cur)

        ttk.Label(frm, text="Related video:").grid(row=4, column=0, sticky="e", padx=6, pady=4)
        ent_text = ttk.Entry(frm, width=60)
        ent_text.grid(row=4, column=1, sticky="we")
        ent_text.insert(0, text_cur)

        import datetime as _dt
        if pd_cur:
            try:
                init_date = _dt.datetime.strptime(pd_cur, "%m/%d/%Y").date()
            except Exception:
                init_date = _dt.date.today()
        else:
            init_date = _dt.date.today()

        ttk.Label(frm, text="Publish date:").grid(row=5, column=0, sticky="e", padx=6, pady=4)
        ent_pd = DateEntry(frm, width=12, date_pattern="mm/dd/yyyy")
        ent_pd.grid(row=5, column=1, sticky="w")
        ent_pd.set_date(init_date)

        ttk.Label(frm, text="Publish time:").grid(row=6, column=0, sticky="e", padx=6, pady=4)
        try:
            h_cur, m_cur = (pt_cur.split(":") if pt_cur else ("", ""))
        except Exception:
            h_cur, m_cur = ("", "")

        hours = [f"{i:02d}" for i in range(24)]
        minutes = [f"{i:02d}" for i in range(0, 60, 5)]

        cb_h = ttk.Combobox(frm, values=hours, width=3, state="readonly")
        cb_h.grid(row=6, column=1, sticky="w", padx=(0, 2))
        cb_h.set(h_cur if h_cur in hours else "00")
        ttk.Label(frm, text=":").grid(row=6, column=1, padx=(50, 0), sticky="w")
        cb_m = ttk.Combobox(frm, values=minutes, width=3, state="readonly")
        cb_m.grid(row=6, column=1, padx=(65, 0), sticky="w")
        cb_m.set(m_cur if m_cur in minutes else "00")

        frm.columnconfigure(1, weight=1)

        def on_save():
            ch = ent_ch.get().strip()
            directory = ent_dir.get().strip()
            t = ent_title.get().strip()
            d = txt_desc.get("1.0", tk.END).strip()
            x = ent_text.get().strip()
            pd = ent_pd.get_date().strftime("%m/%d/%Y")
            pt = f"{cb_h.get()}:{cb_m.get()}"
            if not ch or not t:
                messagebox.showwarning("Missing", "Channel vÃ  Title khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")
                return
            new_vals = (ch, directory, t, d, pd, pt, x)
            self.tree.item(item_id, values=new_vals)
            if 0 <= index < len(self._last_assignments):
                self._last_assignments[index] = new_vals
            self._set_status(f"Updated row {index+1}.")
            win.destroy()

        btns = ttk.Frame(win, padding=(0, 8))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Save", command=on_save).pack(side=tk.LEFT)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.LEFT, padx=6)

        win.update_idletasks()
        w = win.winfo_width(); h = win.winfo_height()
        sw = win.winfo_screenwidth(); sh = win.winfo_screenheight()
        x = (sw // 2) - (w // 2); y = (sh // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
        win.bind("<Return>", lambda e: on_save()); win.bind("<Escape>", lambda e: win.destroy())
        ent_title.focus_set()



    def _delete_selected_rows(self, event=None):
        items = self.tree.selection()
        if not items:
            return
        confirm = messagebox.askyesno("Confirm delete", f"Delete {len(items)} row(s)?")
        if not confirm:
            return
        for item_id in items:
            index = self.tree.index(item_id)
            self.tree.delete(item_id)
            if self._last_assignments and 0 <= index < len(self._last_assignments):
                self._last_assignments.pop(index)
        self._set_status(f"Deleted {len(items)} row(s).")

    def _show_tree_menu(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        if item_id not in self.tree.selection():
            self.tree.selection_set(item_id)

        index = self.tree.index(item_id)

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(
            label="Edit Values",
            command=lambda iid=item_id, idx=index: self._edit_row_dialog(iid, idx)
        )
        menu.add_command(label="Delete", command=lambda: self._delete_selected_rows())
        menu.post(event.x_root, event.y_root)


    def _open_profile_manager(self):
        group_file = self.group_file_var.get().strip()
        if not group_file:
            messagebox.showwarning("No group", "HÃ£y chá»n má»™t group trÆ°á»›c.")
            return
        csv_path = os.path.join(GROUPS_DIR, f"{group_file}.csv")

        win = tk.Toplevel(self)
        win.title(f"Profile Manager - {group_file}")
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Danh sÃ¡ch channel (má»—i dÃ²ng 1 channel):").pack(anchor="w")
        txt = tk.Text(frm, width=50, height=20)
        txt.pack(fill=tk.BOTH, expand=True)

        for ch in self._channels_cache:
            txt.insert(tk.END, ch + "\n")

        def save_profiles():
            lines = [line.strip() for line in txt.get("1.0", tk.END).splitlines() if line.strip()]
            if not lines:
                messagebox.showwarning("Empty", "Danh sÃ¡ch channel khÃ´ng Ä‘Æ°á»£c Ä‘á»ƒ trá»‘ng.")
                return
            with open(csv_path, "w", encoding="utf-8") as f:
                for ch in lines:
                    f.write(ch + "\n")

            self._channels_cache = lines
            self.channel_count_lbl.config(text=f"{len(lines)} channels")
            self._update_profile_combo()
            self._on_mode_change()
            self._schedule_preview()
            self._set_status(f"Saved {len(lines)} channels to {group_file}")
            win.destroy()

        btns = ttk.Frame(win, padding=6)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Save", command=save_profiles).pack(side=tk.LEFT)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.LEFT, padx=6)

        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x, y = (sw // 2) - (w // 2), (sh // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _add_group(self):
        name = sd.askstring("Add Group", "Enter new group name:")
        if not name:
            return
        filename = name + ".csv"
        path = os.path.join(GROUPS_DIR, filename)
        if os.path.exists(path):
            messagebox.showwarning("Exists", f"Group '{name}' already exists")
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("")
            self._set_status(f"Created new group: {name}")
            self._refresh_group_files()
            self.group_file_var.set(name)
            self._load_channels()
        except Exception as e:
            messagebox.showerror("Error", f"Error when creating group:\n{e}")

    def _delete_group(self):
        name = self.group_file_var.get().strip()
        if not name:
            messagebox.showwarning("No group", "Select a group to delete first.")
            return
        confirm = messagebox.askyesno("Confirm delete", f"Delete group '{name}' ?")
        if not confirm:
            return
        path = os.path.join(GROUPS_DIR, name + '.csv')
        try:
            if os.path.exists(path):
                os.remove(path)
            self._set_status(f"Deleted group: '{name}'")
            self._refresh_group_files()
        except Exception as e:
            messagebox.showerror("Error", f'Error when deleting group: \n{e}')

    def _map_group_folder(self):
        name = self.group_file_var.get().strip()
        if not name:
            messagebox.showwarning("No group", "Select group first.")
            return

        folder = filedialog.askdirectory(title=f"Select folder for '{name}' (group or channel)")
        if not folder:
            return
        folder = os.path.abspath(folder)

        # Quyáº¿t Ä‘á»‹nh key ghi vÃ o file config
        active_profile = self.selected_profile_var.get().strip()
        use_profile_key = (self.mode_var.get() == "channels" and bool(active_profile))

        key_plain = name
        key_csv   = f"{name}.csv"
        if use_profile_key:
            # Map riÃªng cho profile á»Ÿ channel mode
            key_to_write = f"{name}|{active_profile}"
            key_to_write_csv = f"{name}.csv|{active_profile}"
            keys_to_remove = {key_to_write, key_to_write_csv}
            status_target = f"{name} | {active_profile}"
        else:
            # Map theo group cho cÃ¡c mode khÃ¡c
            key_to_write = key_plain
            key_to_write_csv = key_csv
            keys_to_remove = {key_plain, key_csv}
            status_target = name

        # Äá»c & ghi láº¡i file config, thay key tÆ°Æ¡ng á»©ng
        lines = []
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if ":" not in line:
                        continue
                    k, _ = line.split(":", 1)
                    k = k.strip()
                    if k in keys_to_remove:
                        continue
                    lines.append(line)

        lines.append(f"{key_to_write}:{folder}")

        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + ("\n" if lines else ""))
            self._set_status(f"Mapped '{status_target}' â†’ {folder}")
        except Exception as e:
            messagebox.showerror("Error", f"Error when write:\n{e}")
            return

        # cáº­p nháº­t preview/status theo map má»›i
        self._schedule_preview()
        self._refresh_channel_stats_label()

        # --- Cáº­p nháº­t láº¡i label sá»‘ lÆ°á»£ng channel + path map ---
        try:
            group_name = self.group_file_var.get().strip()
            if group_name:
                count = len(self._channels_cache)
                current_profile = self.selected_profile_var.get().strip() if self.mode_var.get() == "channels" else None
                mapped_dir = self._get_mapped_folder(group_name, current_profile)
                if mapped_dir:
                    text = f"{count} channels | {mapped_dir}"
                else:
                    text = f"{count} channels | (no folder)"
                self.channel_count_lbl.config(text=text)
        except Exception:
            # náº¿u lá»—i thÃ¬ thÃ´i, khÃ´ng lÃ m crash app
            pass



    def _check_for_updates(self):
        def worker():
            try:
                self._set_status("Checking for updates...")
                msg = check_and_update_safe(UPDATE_MANIFEST, APP_VERSION, verify_hash=True)
                print(f"Update from {UPDATE_MANIFEST}")
                self._set_status(msg)
                if msg.startswith("Installed update") or "Cáº­p nháº­t lÃªn" in msg:
                    if messagebox.askyesno("Update installed", "Restart to apply?"):
                        self._restart_app()
            except Exception as e:
                print(f"Update from {UPDATE_MANIFEST}")
                messagebox.showerror("Update error", str(e))
                self._set_status("Update failed.")
        threading.Thread(target=worker, daemon=True).start()

    def _restart_app(self):
        if self._update_restarted:
            return  # trÃ¡nh restart láº§n 2
        self._update_restarted = True

        python = sys.executable
        script = os.path.abspath(sys.argv[0])
        args = sys.argv[1:]
        subprocess.Popen([python, script] + args, shell=False)
        self.destroy()
        sys.exit(0)


    def _auto_check_update(self):
        def worker():
            try:
                info = check_update_only(UPDATE_MANIFEST, APP_VERSION)
                if info.get("has_update"):
                    new_ver = info["latest_version"]
                    if messagebox.askyesno(
                        "Has new update!!!",
                        f"Version {new_ver} is released.  Do you want to update now?"
                    ):
                        self._set_status("Downloading and installing update...")
                        msg = check_and_update_safe(UPDATE_MANIFEST, APP_VERSION, verify_hash=True)
                        self._set_status(msg)

                else:
                    print(info.get("message", "Already the lastes version"))
            except Exception as e:
                print(f"Error when updating: {e}")

        threading.Thread(target=worker, daemon=True).start()
    
    def _on_mode_change(self):
        if self.mode_var.get() == 'channels':
            self.profile_slot.pack(side=tk.LEFT, padx=(8,0))
            # báº£o Ä‘áº£m toggle hiá»‡n
            if hasattr(self, "_mon_label"):
                self._mon_label.grid(row=0, column=2, padx=(16, 6))
            if hasattr(self, "_mon_container"):
                self._mon_container.grid(row=0, column=3, padx=(0, 0))
            self._render_monetize_toggle()
        else:
            self.profile_slot.pack_forget()
            # áº©n toggle khi khÃ´ng á»Ÿ channel mode
            if hasattr(self, "_mon_label"):
                self._mon_label.grid_forget()
            if hasattr(self, "_mon_container"):
                self._mon_container.grid_forget()

        # chá»‰ save khi Ä‘Ã£ cÃ³ profile
        if self.selected_profile_var.get().strip() and not getattr(self, "_restoring", False):
            self._save_group_settings()
                
    def _update_profile_combo(self):
        self.profile_combo['values'] = self._channels_cache or []
        cur = self.selected_profile_var.get().strip()

        if self.mode_var.get() == 'channels':
            # á»ž channel mode: luÃ´n cá»‘ gáº¯ng cÃ³ 1 profile há»£p lá»‡
            if (not cur) or (cur not in self._channels_cache):
                if self._channels_cache:
                    self.selected_profile_var.set(self._channels_cache[0])
        else:
            # á»ž profile mode: náº¿u selection cÅ© khÃ´ng cÃ²n há»£p lá»‡ thÃ¬ clear
            if cur and cur not in self._channels_cache:
                self.selected_profile_var.set('')

    def _save_group_settings(self):
        group = self.group_file_var.get().strip()
        profile = self.selected_profile_var.get().strip() 
        if not group:
            return

        if group not in self._group_settings:
            self._group_settings[group] = {}

        monetize = self._monetization_vars.get(profile, self.monetization_var.get())
        move_folder = self.move_folder_var.get().strip()

        if self.mode_var.get() == "channels" and profile:
            self._group_settings[group][profile] = {
                "mode": "channels",
                "monetization": monetize,
                "move_folder": move_folder
            }
        else:
            # LÆ°u chung cho group
            self._group_settings[group]["__group__"] = {
                "mode": "titles",
                "move_folder": move_folder
            }

        self._group_settings[group]["__meta__"] = {
            "mode": self.mode_var.get(),
            "last_profile": profile
        }

        save_group_settings(self._group_settings)


    def _load_folder_map(self):
        mapping = {}
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or ":" not in line:
                        continue
                    k, v = line.split(":", 1)
                    mapping[k.strip()] = v.strip()
        return mapping
    
    def _get_mapped_folder(self, group_name: str, profile_name: str = None) -> str:
        m = self._load_folder_map()
        keys = []
        if profile_name and self.mode_var.get() == "channels":
            keys.extend([f"{group_name}|{profile_name}", f"{group_name}.csv|{profile_name}"])
        keys.extend([group_name, f"{group_name}.csv"])
        for k in keys:
            folder = m.get(k, "")
            if folder and os.path.isdir(folder):
                return folder
        return ""
    
    def _toggle_monetization(self):
        self.monetization_var.set(not self.monetization_var.get())
        self._render_monetize_toggle() 
        profile = self.selected_profile_var.get().strip()
        if profile:
            self._monetization_vars[profile] = self.monetization_var.get()
        self._save_group_settings()
        self._set_status(f"Monetization {'ON' if self.monetization_var.get() else 'OFF'} for {profile or 'group'}.")
        
    def _build_monetize_toggle(self, parent):
        self._mon_label = ttk.Label(parent, text="Monetization")
        self._mon_container = ttk.Frame(parent)
        self._mon_switch = tk.Canvas(self._mon_container, width=46, height=24,
                                    highlightthickness=0, bd=0)
        self._mon_switch.pack()
        self._mon_switch.configure(cursor="hand2")     # trá» tay
        self._mon_switch.bind("<Button-1>", lambda e: self._toggle_monetization())

        self._render_monetize_toggle()

    def _render_monetize_toggle(self):
        if not hasattr(self, "_mon_switch"):
            return
        cv = self._mon_switch
        cv.delete("all")

        on = bool(self.monetization_var.get())
        track = "#4CAF50" if on else "#FF6B6B"
        knob_x = 26 if on else 2  # knob ~18px

        # Track 'pill'
        cv.create_oval(1, 1, 23, 23, fill=track, outline=track)
        cv.create_oval(23, 1, 45, 23, fill=track, outline=track)
        cv.create_rectangle(12, 1, 34, 23, fill=track, outline=track)

        # Knob (tráº¯ng)
        cv.create_oval(knob_x, 3, knob_x + 18, 21, fill="#FFFFFF", outline="#DDDDDD")

    def _start_init_in_bg(self):
        threading.Thread(target=self._finish_startup_safe, daemon=True).start()

    def _finish_startup_safe(self):
        try:
            # B1: load group list on UI thread
            self.after(0, lambda: self._refresh_group_files(load_channels=False))

            # B2: restore last group, then load channels after UI is visible
            last_group = ""
            last_group_path = os.path.join(os.path.dirname(__file__), "last_group.txt")
            if os.path.exists(last_group_path):
                with open(last_group_path, "r", encoding="utf-8") as f:
                    last_group = f.read().strip()

            if last_group:
                self.after(0, lambda: self.group_file_var.set(last_group))
            self.after(100, self._load_channels)

            # B3: init preview binding and auto update
            self.after(0, self._bind_text_preview)
            self.after(1500, self._auto_check_update)
        except Exception as e:
            import traceback
            traceback.print_exc()
        finally:
            pass

    def _equalize_inputs(self, *_):
        if not hasattr(self, "_inputs_paned"): 
            return
        p = self._inputs_paned
        try:
            p.update_idletasks()
            total = p.winfo_width() or p.master.winfo_width() or 800
            pane_count = max(1, len(self._inputs_panes))
            each = max(100, total // pane_count)
            for fr in self._inputs_panes:
                p.paneconfig(fr, width=each, minsize=100)
            try:
                for idx in range(pane_count - 1):
                    p.sash_place(idx, each * (idx + 1), 0)
            except Exception:
                pass
        except Exception:
            pass
    

    def _on_tree_click(self, event):
        region = self.tree.identify('region', event.x, event.y)
        item_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)

        if region == 'nothing' or not item_id:
            self._clear_selection_and_editor()
            return
            
        if region != 'cell' or not col_id:
            return

        col_index = int(col_id[1:]) - 1
        self.tree.selection_set(item_id)
        self.tree.focus(item_id)

        bbox = self.tree.bbox(item_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            return

        old_values = list(self.tree.item(item_id, "values"))
        old_text = old_values[col_index] if col_index < len(old_values) else ""

        # Náº¿u Ä‘Ã£ cÃ³ editor thÃ¬ destroy trÆ°á»›c
        self._destroy_cell_editor()

        editor = tk.Entry(self.tree)
        self._cell_editor = editor
        editor.place(x=x, y=y, width=w, height=h)
        editor.insert(0, old_text)

        def _focus_and_select():
            try:
                editor.focus_set()
                editor.select_range(0, tk.END)
            except Exception:
                pass
        self.after(1, _focus_and_select)

        def _finish(save: bool):
            new_text = editor.get().strip() if save else old_text
            self._destroy_cell_editor()

            if not save:
                return

            values = list(self.tree.item(item_id, "values"))
            values += [""] * max(0, col_index + 1 - len(values))
            values[col_index] = new_text
            self.tree.item(item_id, values=values)

            if self._last_assignments:
                try:
                    row_idx = self.tree.index(item_id)
                    if 0 <= row_idx < len(self._last_assignments):
                        row_vals = list(self._last_assignments[row_idx])
                        row_vals += [""] * max(0, len(values) - len(row_vals))
                        row_vals[:len(values)] = values
                        self._last_assignments[row_idx] = tuple(row_vals)
                except Exception:
                    pass

            self._set_status(
                f"Updated row {self.tree.index(item_id)+1}, column {col_index+1}."
            )

        editor.bind("<Return>", lambda e: _finish(True))
        editor.bind("<Escape>", lambda e: _finish(False))
        editor.bind("<FocusOut>", lambda e: _finish(True))

    def _on_tree_single_click(self, event):
        region = self.tree.identify('region', event.x, event.y)
        item_id = self.tree.identify_row(event.y)

        if region == 'nothing' or not item_id:
            self._clear_selection_and_editor()
            return
        
    def _destroy_cell_editor(self):
        if getattr(self, "_cell_editor", None) is not None:
            try:
                self._cell_editor.destroy()
            except Exception:
                pass
            self._cell_editor = None

    def _clear_selection_and_editor(self):
        self.tree.selection_remove(self.tree.selection())
        self._destroy_cell_editor()

    def _select_all(self, event=None):
        items = self.tree.get_children()
        self.tree.selection_set(items)
        return "break" 
    def _clear_selection(self, event=None):
        self.tree.selection_remove(self.tree.selection())
        return "break"
    
    def _global_click(self, event):
        widget = event.widget
        if isinstance(widget, (tk.Button, ttk.Button)):
            return
        if isinstance(widget, ttk.Treeview) or widget is self.tree:
            return
        if getattr(self, "_cell_editor", None) is not None:
            if widget is self._cell_editor:
                return
        self._clear_selection_and_editor()

    def _refresh_channel_stats_label(self):
        try:
            group_name = self.group_file_var.get().strip()
            if not group_name:
                self.channel_count_lbl.config(text="0 channels | (no folder)")
                return

            count = len(self._channels_cache)
            # á»ž channel mode thÃ¬ dÃ¹ng mapping theo profile, cÃ²n láº¡i dÃ¹ng theo group
            profile = self.selected_profile_var.get().strip() if self.mode_var.get() == "channels" else None
            mapped_dir = self._get_mapped_folder(group_name, profile)

            if mapped_dir:
                text = f"{count} channels | {mapped_dir}"
            else:
                text = f"{count} channels | (no folder)"

            self.channel_count_lbl.config(text=text)
        except Exception as e:
            print("Error refreshing channel stats:", e)

if __name__ == "__main__":
    rearrange_and_delete_junk_files() # rearrange files first
    app = App()
    app.mainloop()



