import os
import threading
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from module import list_group_csvs, read_channels_from_csv, normalize_lines, assign_pairs, load_group_dirs, load_used_videos, get_mp4_filename, load_group_config, save_group_config
from hyperparameter import (
    APP_TITLE,
    GROUPS_DIR,
    OUTPUT_DIR,
)
from tkcalendar  import DateEntry
from tkcalendar import Calendar
from openpyxl import Workbook,load_workbook
from openpyxl.utils import get_column_letter
from openpyxl.styles import Font
from random_vids import get_random_unused_mp4
import glob
from ui_theme import setup_theme
from excel_helper import save_assignments_to_excel, combine_excels

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        style = ttk.Style()
        style.theme_use("clam") 
        setup_theme(style, self)

        self.title(APP_TITLE)
        self.state("zoomed") 
        self.minsize(880, 580)

        menubar = tk.Menu(self)
        self.config(menu=menubar)
        profiles_menu = tk.Menu(menubar, tearoff=0)
        profiles_menu.add_command(label="Manage Profiles", command=self._open_profile_manager)
        profiles_menu.add_command(label="Add Group", command=self._add_group)
        menubar.add_cascade(label="Profiles", menu=profiles_menu)



        self.group_file_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="titles") 
        self.status_var = tk.StringVar(value="Ready.")

        # Cache & state
        self._channels_cache = []
        self._last_assignments = None  # list[(channel, title, desc, publish_date, publish_time)]

        # Date/Time header controls state
        self.date_entry = None  
        now = datetime.datetime.now()
        self.time_h_var = tk.StringVar(value=f"{now.hour:02d}")
        self.time_m_var = tk.StringVar(value=f"{now.minute:02d}")
        self.step_min_var = tk.IntVar(value=30) 

        self._build_header()
        self._build_inputs()
        self._build_preview()
        self._build_footer()
        self._refresh_group_files()
        self._bind_text_preview()

    # ---------- Header ----------

    def _schedule_preview(self):
        if hasattr(self, "_preview_job"):
            self.after_cancel(self._preview_job)
        self._preview_job = self.after(500, self._preview)  # 500ms delay

    def _bind_text_preview(self):
        def on_change(event):
            event.widget.edit_modified(False)
            self._schedule_preview()
        self.txt_titles.bind("<<Modified>>", on_change)
        self.txt_descs.bind("<<Modified>>", on_change)
        self.txt_times.bind("<<Modified>>", on_change)

    def _build_header(self):
        frm = ttk.Frame(self, padding=(10, 10, 10, 0))
        frm.pack(fill=tk.X)

        ttk.Label(frm, text="Group:").grid(row=0, column=0, sticky="w")
        self.group_combo = ttk.Combobox(frm, textvariable=self.group_file_var, state="readonly", width=48)
        self.group_combo.grid(row=0, column=1, sticky="w", padx=6)
        self.group_combo.bind("<<ComboboxSelected>>", lambda e: self._load_channels())

        self.channel_count_lbl = ttk.Label(frm, text="0 channels")
        self.channel_count_lbl.grid(row=0, column=4, sticky="w", padx=(12, 0))
        frm.columnconfigure(1, weight=1)

        # Distribution mode
        frm2 = ttk.Frame(self, padding=(10, 6, 10, 0))
        frm2.pack(fill=tk.X)
        ttk.Label(frm2, text="Distribution mode:").pack(side=tk.LEFT)
        ttk.Radiobutton(frm2, text="Repeat", variable=self.mode_var, value="titles").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(frm2, text="No Repeat", variable=self.mode_var, value="channels").pack(side=tk.LEFT, padx=(8, 0))

        # Date/Time controls (apply to ALL rows)
        frm3 = ttk.Frame(self, padding=(10, 6, 10, 0))
        frm3.pack(fill=tk.X)

        ttk.Label(frm3, text="Publish date:").pack(side=tk.LEFT)

        self.date_entry = DateEntry(
            frm3,
            width=12,
            date_pattern="mm/dd/yyyy",   # định dạng ngày
            state="readonly"             # không cho gõ tay, chỉ chọn
        )
        self.date_entry.set_date(datetime.date.today())
        self.date_entry.pack(side=tk.LEFT, padx=(6, 16))


        ttk.Label(frm3, text="Publish time:").pack(side=tk.LEFT)

        hours = [f"{i:02d}" for i in range(24)]
        minutes = [f"{i:02d}" for i in range(0, 60, 5)]

        cb_h = ttk.Combobox(frm3, values=hours, width=3, textvariable=self.time_h_var, state="readonly")
        cb_h.pack(side=tk.LEFT, padx=(6, 2))
        ttk.Label(frm3, text=":").pack(side=tk.LEFT)
        cb_m = ttk.Combobox(frm3, values=minutes, width=3, textvariable=self.time_m_var, state="normal")
        cb_m.pack(side=tk.LEFT, padx=(2, 12))

        ttk.Label(frm3, text="Step (min):").pack(side=tk.LEFT)
        sp_step = tk.Spinbox(frm3, from_=0, to=1440, increment=5, width=5, textvariable=self.step_min_var)
        sp_step.pack(side=tk.LEFT, padx=(6, 12))

        ttk.Button(frm3, text="Apply Datetime to all", command=self._apply_date_time_all).pack(side=tk.LEFT, padx=(12, 0))


    # ---------- Inputs ----------
    def _build_inputs(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # === Titles ===
        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        ttk.Label(left, text="Titles (one per line)").pack(anchor="w")
        self.txt_titles = tk.Text(left, height=12, wrap=tk.WORD)
        self.txt_titles.pack(fill=tk.BOTH, expand=True)

        # === Descriptions ===
        mid = ttk.Frame(frm)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        ttk.Label(mid, text="Descriptions (1 line for all, or multiple lines)").pack(anchor="w")
        self.txt_descs = tk.Text(mid, height=12, wrap=tk.WORD)
        self.txt_descs.pack(fill=tk.BOTH, expand=True)

        # === Time column ===
        right = ttk.Frame(frm)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        ttk.Label(right, text="Time (HH:MM or per line)").pack(anchor="w")
        self.txt_times = tk.Text(right, height=12, wrap=tk.WORD)
        self.txt_times.pack(fill=tk.BOTH, expand=True)

        # === Buttons ===
        btns = ttk.Frame(self, padding=(10, 0, 10, 0))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Clear Inputs", command=self._clear_inputs).pack(side=tk.LEFT, padx=6)


    # ---------- Preview / Tree ----------
    def _build_preview(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        cols = ("channel", "directory", "title", "description", "publish_date", "publish_time")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
        
        for col in cols:
            self.tree.heading(col, text=col.capitalize())
            if col == "description":
                self.tree.column(col, width=420, anchor="w")
            elif col == "title":
                self.tree.column(col, width=300, anchor="w")
            elif col == "channel":
                self.tree.column(col, width=200, anchor="w")
            elif col == "publish_date":
                self.tree.column(col, width=120, anchor="w")
            elif col == "publish_time":
                self.tree.column(col, width=100, anchor="w")
            elif col == "directory":
                self.tree.column(col, width=240, anchor="w")

        vsb = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        # Double-click edit row
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        self.tree.bind("<Delete>", self._delete_selected_rows)
        self.tree.bind("<Button-3>", self._show_tree_menu)


        btns = ttk.Frame(self, padding=(10, 0, 10, 10))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Save Excel", command=self._save_excel).pack(side=tk.LEFT)

    def _build_footer(self):
        bar = ttk.Frame(self, relief=tk.SUNKEN, padding=6)
        bar.pack(fill=tk.X, side=tk.BOTTOM)

        self.move_folder_var = tk.StringVar(value="")  # đường dẫn video mới

        ttk.Label(bar, text="Save to:").pack(side=tk.LEFT, padx=(0, 4))
        ent = ttk.Entry(bar, textvariable=self.move_folder_var, width=50)
        ent.pack(side=tk.LEFT, padx=(0, 4))

        def choose_folder():
            folder = filedialog.askdirectory(title="Chọn thư mục lưu video mới")
            if folder:
                self.move_folder_var.set(folder)
                group_name = self.group_file_var.get().strip()
                if group_name:
                    save_group_config(group_name, folder)

        ttk.Button(bar, text="Browse", command=choose_folder).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(bar, text="Combine", command=self._combine_excels).pack(side=tk.RIGHT)
        ttk.Label(bar, textvariable=self.status_var).pack(side=tk.LEFT)


    # ---------- Actions ----------
    def _refresh_group_files(self):
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
            self.group_file_var.set(groups[0])   # <== set tên không .csv

        self._load_channels()


    

    def _load_channels(self):
        name = self.group_file_var.get().strip()
        if not name:
            return
        csv_path = os.path.join(GROUPS_DIR, name + ".csv")
        channels = read_channels_from_csv(csv_path)
        self._channels_cache = channels
        self.channel_count_lbl.config(text=f"{len(channels)} channels")
        self._set_status(f"Loaded {len(channels)} channels from {name}")
        # Load last used move_folder
        last_folder = load_group_config(name + ".csv")
        self.move_folder_var.set(last_folder)


    def _clear_inputs(self):
        self.txt_titles.delete("1.0", tk.END)
        self.txt_descs.delete("1.0", tk.END)
        self.tree.delete(*self.tree.get_children())
        self._last_assignments = None
        self._set_status("Cleared inputs & preview.")

    def _preview(self):
        group_file = self.group_file_var.get().strip()
        if not group_file:
            messagebox.showwarning("Missing CSV", "Please select a group CSV")
            return

        titles = normalize_lines(self.txt_titles.get("1.0", tk.END))
        descs = normalize_lines(self.txt_descs.get("1.0", tk.END))
        times = normalize_lines(self.txt_times.get("1.0", tk.END))   # <== thêm dòng này
        channels = self._channels_cache
        mode = self.mode_var.get()

        if not titles and not descs:
            self.tree.delete(*self.tree.get_children())
            self._last_assignments = None
            self._set_status("Inputs empty → preview cleared.")
            return

        try:
            assignments = assign_pairs(channels, titles, descs, mode=mode)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        group_dirs = load_group_dirs()
        folder_path = group_dirs.get(group_file)

        used_paths = load_used_videos()
        session_used = set()
        self.tree.delete(*self.tree.get_children())
        extended = []

        for i, (ch, t, d) in enumerate(assignments):

            pt = times[i] if i < len(times) else ""
            #if time ->> date = today
            pd = datetime.date.today().strftime("%m/%d/%Y") if pt else ""

            if folder_path and os.path.isdir(folder_path):
                directory = get_random_unused_mp4(folder_path, used_paths | session_used)
                if directory:
                    session_used.add(directory)
            else:
                directory = ""

            self.tree.insert("", tk.END, values=(ch, directory, t, d, pd, pt))
            extended.append((ch, directory, t, d, pd, pt))

        self._last_assignments = extended
        if mode == "titles":
            self._set_status(f"Previewed {len(assignments)} rows (title-driven; channels cycle if needed).")
        else:
            self._set_status(f"Previewed {len(assignments)} rows (channel-driven).")



    def _save_excel(self):
        if not self._last_assignments:
            messagebox.showwarning("Nothing to save", "Click Preview first.")
            return

        def worker():
            try:
                base = os.path.splitext(self.group_file_var.get().strip())[0] or "group"
                out_name = f"{base}.xlsx"
                out_path = os.path.join(OUTPUT_DIR, out_name)

                save_assignments_to_excel(self._last_assignments, out_path)
                self._set_status(f"Saved Excel: {out_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save Excel:\n{e}")

        threading.Thread(target=worker, daemon=True).start()




    def _set_status(self, msg: str):
        self.status_var.set(msg)

    # ---------- Edit row by double click----------
    def _on_tree_double_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region != "cell":
            return
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        index = self.tree.index(item_id)
        self._edit_row_dialog(item_id, index)


    def _edit_row_dialog(self, item_id, index):
        vals = list(self.tree.item(item_id, "values"))
        vals += [""] * max(0, 6 - len(vals))
        ch_cur, dir_cur, title_cur, desc_cur, pd_cur, pt_cur = vals

        win = tk.Toplevel(self)
        win.title("Edit row")
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        # --- Profile (Combobox) ---
        ttk.Label(frm, text="Profile:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        ent_ch = ttk.Combobox(frm, values=[c for c in self._channels_cache],
                            state="readonly", width=60)
        ent_ch.grid(row=0, column=1, sticky="we")
        ent_ch.set(ch_cur)

        # --- Directory ---
        ttk.Label(frm, text="Directory:").grid(row=1, column=0, sticky="e", padx=6, pady=4)
        ent_dir = ttk.Entry(frm, width=60)
        ent_dir.grid(row=1, column=1, sticky="we")
        ent_dir.insert(0, dir_cur)

        # --- Title ---
        ttk.Label(frm, text="Title:").grid(row=2, column=0, sticky="e", padx=6, pady=4)
        ent_title = ttk.Entry(frm, width=60)
        ent_title.grid(row=2, column=1, sticky="we")
        ent_title.insert(0, title_cur)

        # --- Description ---
        ttk.Label(frm, text="Description:").grid(row=3, column=0, sticky="ne", padx=6, pady=4)
        txt_desc = tk.Text(frm, width=60, height=6, wrap=tk.WORD)
        txt_desc.grid(row=3, column=1, sticky="we")
        txt_desc.insert("1.0", desc_cur)

        # --- Publish date ---
        ttk.Label(frm, text="Publish date:").grid(row=4, column=0, sticky="e", padx=6, pady=4)
        import datetime
        if pd_cur:
            try:
                init_date = datetime.datetime.strptime(pd_cur, "%m/%d/%Y").date()
            except Exception:
                init_date = datetime.date.today()
        else:
            init_date = datetime.date.today()

        ent_pd = DateEntry(frm, width=12, date_pattern="mm/dd/yyyy")
        ent_pd.grid(row=4, column=1, sticky="w")
        ent_pd.set_date(init_date)

        # --- Publish time (giờ/phút dropdown) ---
        ttk.Label(frm, text="Publish time:").grid(row=5, column=0, sticky="e", padx=6, pady=4)

        # Tách giờ:phút cũ
        try:
            h_cur, m_cur = (pt_cur.split(":") if pt_cur else ("", ""))
        except Exception:
            h_cur, m_cur = ("", "")

        hours = [f"{i:02d}" for i in range(24)]
        minutes = [f"{i:02d}" for i in range(0, 60, 5)]  # step 5 phút cho dễ chọn

        cb_h = ttk.Combobox(frm, values=hours, width=3, state="readonly")
        cb_h.grid(row=5, column=1, sticky="w", padx=(0, 2))
        cb_h.set(h_cur if h_cur in hours else "00")

        ttk.Label(frm, text=":").grid(row=5, column=1, padx=(50, 0), sticky="w")

        cb_m = ttk.Combobox(frm, values=minutes, width=3, state="readonly")
        cb_m.grid(row=5, column=1, padx=(65, 0), sticky="w")
        cb_m.set(m_cur if m_cur in minutes else "00")

        frm.columnconfigure(1, weight=1)

        def on_save():
            ch = ent_ch.get().strip()
            directory = ent_dir.get().strip()
            t = ent_title.get().strip()
            d = txt_desc.get("1.0", tk.END).strip()
            pd = ent_pd.get_date().strftime("%m/%d/%Y")
            pt = f"{cb_h.get()}:{cb_m.get()}"

            if not ch or not t:
                messagebox.showwarning("Missing", "Channel và Title không được để trống.")
                return

            new_vals = (ch, directory, t, d, pd, pt)
            self.tree.item(item_id, values=new_vals)

            if 0 <= index < len(self._last_assignments):
                self._last_assignments[index] = new_vals

            self._set_status(f"Updated row {index+1}.")
            win.destroy()

        # --- Buttons ---
        btns = ttk.Frame(win, padding=(0, 8))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Save", command=on_save).pack(side=tk.LEFT)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.LEFT, padx=6)

        # --- Center window ---
        win.update_idletasks()
        w = win.winfo_width()
        h = win.winfo_height()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")


        win.bind("<Return>", lambda e: on_save())
        win.bind("<Escape>", lambda e: win.destroy())
        ent_title.focus_set()



    # ---------- Apply date/time to ALL ----------
    def _apply_date_time_all(self):
    # --- get date ---
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

        # --- get time ---
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
        if step < 0:
            messagebox.showerror("Invalid step", "Step (min) không được âm.")
            return

        base_dt = datetime.datetime(2000, 1, 1, h, m)
        ids = self.tree.get_children()

        for i, iid in enumerate(ids):
            tm = (base_dt + datetime.timedelta(minutes=step)).time()
            time_str = f"{tm.hour:02d}:{tm.minute:02d}"

            vals = list(self.tree.item(iid, "values"))
            vals += [""] * max(0, 6 - len(vals))
            ch, directory, t, desc, _, _ = vals
            new_vals = (ch, directory, t, desc, date_str, time_str)

            self.tree.item(iid, values=new_vals)
            if self._last_assignments and i < len(self._last_assignments):
                self._last_assignments[i] = new_vals    

        self._set_status(f"Tổng cộng có: {len(ids)} dòng.")

    def _combine_excels(self):
        input_dir = "upload"
        output_file = "upload_data.xlsx"
        move_folder = self.move_folder_var.get().strip()

        try:
            count, files = combine_excels(input_dir, output_file, move_folder, get_mp4_filename)
            if count == 0:
                messagebox.showwarning("No files", f"Không tìm thấy file Excel nào trong:\n{input_dir}")
                return
            self._set_status(f"Combined {count} files → {output_file}")
            messagebox.showinfo("Done", f"Combined successfully")
        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi combine:\n{e}")

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

        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Delete", command=lambda: self._delete_selected_rows())
        menu.post(event.x_root, event.y_root)

    def _open_profile_manager(self):
        group_file = self.group_file_var.get().strip()
        if not group_file:
            messagebox.showwarning("No group", "Hãy chọn một group CSV trước.")
            return

        csv_path = os.path.join(GROUPS_DIR, group_file)

        win = tk.Toplevel(self)
        win.title(f"Profile Manager - {group_file}")
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Danh sách channel (mỗi dòng 1 channel):").pack(anchor="w")

        txt = tk.Text(frm, width=50, height=20)
        txt.pack(fill=tk.BOTH, expand=True)

        # load danh sách hiện tại
        for ch in self._channels_cache:
            txt.insert(tk.END, ch + "\n")

        def save_profiles():
            lines = [line.strip() for line in txt.get("1.0", tk.END).splitlines() if line.strip()]
            if not lines:
                messagebox.showwarning("Empty", "Danh sách channel không được để trống.")
                return
            with open(csv_path, "w", encoding="utf-8") as f:
                for ch in lines:
                    f.write(ch + "\n")
            self._channels_cache = lines
            self.channel_count_lbl.config(text=f"{len(lines)} channels")
            self._set_status(f"Saved {len(lines)} channels to {group_file}")
            win.destroy()

        btns = ttk.Frame(win, padding=6)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Save", command=save_profiles).pack(side=tk.LEFT)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.LEFT, padx=6)

        # Center window
        win.update_idletasks()
        w, h = win.winfo_width(), win.winfo_height()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        x, y = (sw // 2) - (w // 2), (sh // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _add_group(self):
        import tkinter.simpledialog as sd

        name = sd.askstring("Add Group", "Enter new group name:")
        if not name:
            return

        if name.lower().endswith(".csv"):
            name = name[:-4]  # bỏ đuôi csv nếu người dùng nhập

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
            self.group_file_var.set(name)   # không .csv
            self._load_channels()
        except Exception as e:
            messagebox.showerror("Error", f"Error when creating group:\n{e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
