import os
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from module import list_group_csvs, read_channels_from_csv, normalize_lines, assign_pairs, load_group_dirs, load_used_videos, get_mp4_filename
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


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        style = ttk.Style()
        style.theme_use("clam") 
        

        # === Dark Theme custom ===
        bg_dark = "#2b2b2b"
        bg_panel = "#3c3f41"
        fg_light = "#f0f0f0"
        accent = "#0078d7"

        # Text widget
        self.option_add("*TEntry*background", bg_panel)
        self.option_add("*TEntry*foreground", fg_light)
        self.option_add("*Text*background", bg_panel)
        self.option_add("*Text*foreground", fg_light)
        self.option_add("*Text*insertBackground", "white")   # con trỏ trắng

        # Spinbox
        style.configure("TSpinbox",
                        fieldbackground=bg_panel,
                        background=bg_panel,
                        foreground=fg_light,
                        arrowsize=14)
        style.map("TSpinbox",
                  fieldbackground=[("readonly", bg_panel)],
                  foreground=[("readonly", fg_light)])
        
        # Radiobutton (Repeat / No Repeat)
        style.configure("TRadiobutton",
                        background=bg_dark,      
                        foreground=fg_light, 
                        font=("Segoe UI", 10))

        style.map("TRadiobutton",
                background=[("active", bg_panel)],   # khi hover
                foreground=[("active", accent)])     # chữ xanh khi hover


        # DateEntry (từ tkcalendar) kế thừa TEntry
        style.configure("DateEntry",
                        fieldbackground=bg_panel,
                        background=bg_panel,
                        foreground=fg_light)

        # Frame & window background đồng bộ
        style.configure("TFrame", background=bg_dark)
        style.configure("TLabelframe", background=bg_dark, foreground=fg_light)
        style.configure("TLabelframe.Label", background=bg_dark, foreground=fg_light)

        # Sửa cả default window bg cho đồng bộ
        self.option_add("*Background", bg_dark)
        self.option_add("*Foreground", fg_light)

        # Set màu nền chính cho cửa sổ
        self.configure(bg=bg_dark)

        # Treeview
        style.configure("Treeview",
                        background=bg_panel,
                        foreground=fg_light,
                        rowheight=28,
                        fieldbackground=bg_panel,
                        font=("Segoe UI", 10))
        style.map("Treeview",
                  background=[("selected", accent)],
                  foreground=[("selected", "white")])   
        # Header của Treeview
        style.configure("Treeview.Heading",
                        font=("Segoe UI", 10, "bold"),
                        background=bg_dark,
                        foreground=fg_light)

        # Button
        style.configure("TButton",
                        background=bg_panel,
                        foreground=fg_light,
                        font=("Segoe UI", 10, "bold"),
                        padding=6)
        style.map("TButton",
                  background=[("active", accent), ("pressed", accent)],
                  foreground=[("active", "white"), ("pressed", "white")])

        # Nhãn
        style.configure("TLabel",
                        background=bg_dark,
                        foreground=fg_light,
                        font=("Segoe UI", 10))

        # Ô nhập
        style.configure("TEntry",
                        fieldbackground=bg_panel,
                        foreground=fg_light,
                        insertcolor="white",  
                        padding=4)

        # Combobox
        style.configure("TCombobox",
                        fieldbackground=bg_panel,
                        background=bg_panel,
                        foreground=fg_light,
                        selectbackground=accent,
                        selectforeground="white",
                        padding=4)
        
        style.map("TCombobox",
                  fieldbackground=[("readonly", bg_panel)],
                  foreground=[("readonly", fg_light)],
                  selectbackground=[("readonly", accent)],
                  selectforeground=[("readonly", "white")])



        self.title(APP_TITLE)
        self.state("zoomed") 
        self.minsize(880, 580)

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
        self.step_min_var = tk.IntVar(value=0) 

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

        # Dùng DateEntry trực tiếp (có sẵn ô chọn ngày + popup nhỏ gọn)
        self.date_entry = DateEntry(
            frm3,
            width=12,
            date_pattern="dd/mm/yyyy",   # định dạng ngày
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

        left = ttk.Frame(frm)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        ttk.Label(left, text="Titles (one per line)").pack(anchor="w")
        self.txt_titles = tk.Text(left, height=12, wrap=tk.WORD)
        self.txt_titles.pack(fill=tk.BOTH, expand=True)

        right = ttk.Frame(frm)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))
        ttk.Label(right, text="Descriptions (1 line for all, or multiple lines)").pack(anchor="w")
        self.txt_descs = tk.Text(right, height=12, wrap=tk.WORD)
        self.txt_descs.pack(fill=tk.BOTH, expand=True)

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

        ttk.Button(bar, text="Browse", command=choose_folder).pack(side=tk.LEFT, padx=(0, 8))

        ttk.Button(bar, text="Combine", command=self._combine_excels).pack(side=tk.RIGHT)
        ttk.Label(bar, textvariable=self.status_var).pack(side=tk.LEFT)



    # ---------- Actions ----------
    def _refresh_group_files(self):
        files = list_group_csvs(GROUPS_DIR)
        self.group_combo["values"] = files
        cur = self.group_file_var.get()
        if not files:
            self.group_file_var.set("")
            self.channel_count_lbl.config(text="0 channels")
            self._set_status(f"No CSV files in: {GROUPS_DIR}")
            return
        if cur not in files:
            self.group_file_var.set(files[0])
        self._load_channels()

    def _load_channels(self):
        name = self.group_file_var.get().strip()
        if not name:
            return
        csv_path = os.path.join(GROUPS_DIR, name)
        channels = read_channels_from_csv(csv_path)
        self._channels_cache = channels
        self.channel_count_lbl.config(text=f"{len(channels)} channels")
        self._set_status(f"Loaded {len(channels)} channels from {name}.")

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

        group_dirs = load_group_dirs()  # {group.csv: folder_path}
        folder_path = group_dirs.get(group_file)

        used_paths = load_used_videos()   # load from log.txt
        session_used = set()              # avoid duplicate in preview session
        self.tree.delete(*self.tree.get_children())
        extended = []

        for ch, t, d in assignments:
            pd, pt = "", ""
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
        base = os.path.splitext(self.group_file_var.get().strip())[0] or "group"
        out_name = f"{base}.xlsx"

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out_path = os.path.join(OUTPUT_DIR, out_name)
        existed = os.path.exists(out_path)

        try:
            wb = Workbook()
            ws = wb.active
            ws.title = "Assignments"

            # ghi header
            headers = ["channel", "directory", "title", "description", "publish_date", "publish_time"]
            ws.append(headers)
            for col_idx, h in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=col_idx)
                cell.font = Font(bold=True)

            # ghi dữ liệu từ preview
            for ch, directory, t, d, pd, pt in self._last_assignments:
                ws.append([ch, directory, t, d, pd, pt])

            # Auto width (approx)
            desc_idx = headers.index("description") + 1
            for col_idx in range(1, ws.max_column + 1):
                col_letter = get_column_letter(col_idx)
                max_len = 0
                for row in ws.iter_rows(min_row=1, max_row=ws.max_row,
                                        min_col=col_idx, max_col=col_idx):
                    val = row[0].value
                    if val is None:
                        continue
                    s = str(val)
                    if col_idx == desc_idx:
                        s = s[:120]
                    max_len = max(max_len, len(s))

                header_name = headers[col_idx - 1]
                if header_name in ("publish_date", "publish_time"):
                    ws.column_dimensions[col_letter].width = max(12, min(max_len + 2, 18))
                else:
                    ws.column_dimensions[col_letter].width = min(max_len + 2, 80)

            ws.auto_filter.ref = ws.dimensions
            ws.freeze_panes = "A2"

            # Ghi đè nếu tồn tại
            if existed:
                try:
                    os.remove(out_path)
                except PermissionError:
                    messagebox.showerror(
                        "File is open",
                        f"Can't write to file when file is opening:\n{out_path}\nPlz close file."
                    )
                    return

            wb.save(out_path)

            self._set_status(f"Saved Excel: {out_path}" + (" (overwritten)" if existed else ""))
            messagebox.showinfo("Saved",
                               "Save successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save Excel:\n{e}")



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
        # đảm bảo luôn có 6 phần tử
        vals += [""] * max(0, 6 - len(vals))
        ch_cur, dir_cur, title_cur, desc_cur, pd_cur, pt_cur = vals

        win = tk.Toplevel(self)
        win.title("Edit row")
        win.transient(self)
        win.grab_set()

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Profile:").grid(row=0, column=0, sticky="e", padx=6, pady=4)
        ent_ch = ttk.Entry(frm, width=60)
        ent_ch.grid(row=0, column=1, sticky="we")
        ent_ch.insert(0, ch_cur)

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

        ttk.Label(frm, text="Publish date (DD/MM/YYYY):").grid(row=4, column=0, sticky="e", padx=6, pady=4)
        ent_pd = ttk.Entry(frm, width=20)
        ent_pd.grid(row=4, column=1, sticky="w")
        ent_pd.insert(0, pd_cur)

        ttk.Label(frm, text="Publish time (HH:MM):").grid(row=5, column=0, sticky="e", padx=6, pady=4)
        ent_pt = ttk.Entry(frm, width=20)
        ent_pt.grid(row=5, column=1, sticky="w")
        ent_pt.insert(0, pt_cur)


        frm.columnconfigure(1, weight=1)

        def is_valid_date(s: str) -> bool:
            if not s.strip():
                return True
            try:
                datetime.datetime.strptime(s.strip(), "%d/%m/%Y")
                return True
            except ValueError:
                return False

        def is_valid_time(s: str) -> bool:
            if not s.strip():
                return True
            try:
                datetime.datetime.strptime(s.strip(), "%H:%M")
                return True
            except ValueError:
                return False

        def on_save():
            directory = ent_dir.get().strip()
            ch = ent_ch.get().strip()
            t = ent_title.get().strip()
            d = txt_desc.get("1.0", tk.END).strip()
            pd = ent_pd.get().strip()
            pt = ent_pt.get().strip()

            if not ch or not t:
                messagebox.showwarning("Missing", "Channel và Title không được để trống.")
                return
            if not is_valid_date(pd):
                messagebox.showerror("Invalid date", "Publish date phải dạng DD/MM/YYYY hoặc để trống.")
                return
            if not is_valid_time(pt):
                messagebox.showerror("Invalid time", "Publish time phải dạng HH:MM (24h) hoặc để trống.")
                return

            new_vals = (ch,directory, t, d, pd, pt)
            self.tree.item(item_id, values=new_vals)

            if 0 <= index < len(self._last_assignments):
                self._last_assignments[index] = new_vals

            self._set_status(f"Updated row {index+1}.")
            win.destroy()

        btns = ttk.Frame(win, padding=(0, 8))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Save", command=on_save).pack(side=tk.LEFT)
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side=tk.LEFT, padx=6)

        win.bind("<Return>", lambda e: on_save())
        win.bind("<Escape>", lambda e: win.destroy())
        ent_title.focus_set()

    # ---------- Apply date/time to ALL ----------
    def _apply_date_time_all(self):
    # --- Lấy ngày ---
        if hasattr(self.date_entry, "get_date"):
            try:
                d = self.date_entry.get_date()
                date_str = d.strftime("%d/%m/%Y")
            except Exception:
                date_str = str(self.date_entry.get()).strip()
        else:
            date_str = str(self.date_entry.get()).strip()

        try:
            datetime.datetime.strptime(date_str, "%d/%m/%Y")
        except ValueError:
            messagebox.showerror("Invalid date", "Định dạng ngày phải là DD/MM/YYYY.")
            return

        # --- Lấy giờ phút ---
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
            tm = (base_dt + datetime.timedelta(minutes=i * step)).time()
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


        input_dir = 'upload'
        output_file = 'upload_data.xlsx'

        pattern = os.path.join(input_dir, "*.xlsx")
        files = glob.glob(pattern)

        if not files:
            messagebox.showwarning("No files", f"Không tìm thấy file Excel nào trong:\n{input_dir}")
            return

        wb_out = Workbook()
        ws_out = wb_out.active
        ws_out.title = "Combined"

        header_written = False
        row_idx = 1
        move_folder = self.move_folder_var.get().strip()

        for file in files:
            try:
                wb = load_workbook(file)
                ws = wb.active

                max_row = ws.max_row
                max_col = ws.max_column

                if not header_written:
                    # copy header gốc
                    for col in range(1, max_col + 1):
                        ws_out.cell(row=1, column=col).value = ws.cell(row=1, column=col).value
                    # thêm cột mới move_folder
                    ws_out.cell(row=1, column=max_col + 1).value = "move_folder"
                    header_written = True
                    row_idx += 1

                for r in range(2, max_row + 1):
                    row_values = []
                    for c in range(1, max_col + 1):
                        val = ws.cell(row=r, column=c).value
                        row_values.append(val)

                    # giữ nguyên directory (cột 2)
                    directory_val = row_values[1] if len(row_values) > 1 else ""

                    # tạo move_folder = thư mục mới + tên file từ directory
                    filename = get_mp4_filename(directory_val)
                    move_path = os.path.join(move_folder, filename) if filename else ""

                    # ghi lại các cột cũ
                    for c, val in enumerate(row_values, start=1):
                        ws_out.cell(row=row_idx, column=c).value = val

                    # ghi thêm cột move_folder
                    ws_out.cell(row=row_idx, column=max_col + 1).value = move_path

                    row_idx += 1

            except Exception as e:
                messagebox.showerror("Error", f"Lỗi khi đọc {file}:\n{e}")
                return

        try:
            os.makedirs(os.path.dirname(output_file) or ".", exist_ok=True)
            if os.path.exists(output_file):
                os.remove(output_file)
            wb_out.save(output_file)

            messagebox.showinfo("Done", f"Đã gộp và lưu vào:\n{output_file}")
            self._set_status(f"Combined {len(files)} files → {output_file}")

            #delete after combine
            for file in files:
                try:
                    wb = load_workbook(file)
                    ws = wb.active

                    max_row = ws.max_row
                    max_col = ws.max_column
                    
                    for row in ws.iter_rows(min_row=2, max_row=max_row, max_col=max_col):
                        for cell in row:
                            cell.value = None

                    wb.save(file)
                except Exception as e:
                    messagebox.showerror("Error", f"Lỗi khi xóa data trong file: {file} \n{e} ")

            self._set_status(f"Cleared data in {len(files)} files in {input_dir}")

        except Exception as e:
            messagebox.showerror("Error", f"Lỗi khi lưu file:\n{e}")



if __name__ == "__main__":
    app = App()
    app.mainloop()
