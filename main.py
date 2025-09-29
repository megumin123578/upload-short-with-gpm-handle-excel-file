# distribute_gui.py
import os
import csv
import itertools
import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "Distribute Titles to Channels (group/*.csv)"
GROUPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "group")

CHANNEL_HEADER_HINTS = [
    "channel", "kênh", "kenh", "channel_id", "channel name", "channel_name", "name", "id"
]

def list_group_csvs(groups_dir: str):
    if not os.path.isdir(groups_dir):
        return []
    files = []
    for name in os.listdir(groups_dir):
        p = os.path.join(groups_dir, name)
        nl = name.lower()
        if os.path.isfile(p) and nl.endswith(".csv"):
            if "__assignments_" in nl or nl.startswith("assignments_"):
                continue
            files.append(name)
    return sorted(files)

def read_channels_from_csv(csv_path: str):
    channels = []
    if not os.path.isfile(csv_path):
        return channels
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return channels
    header = [c.strip() for c in rows[0]] if rows and rows[0] else []
    col_idx = None
    if header:
        lower_header = [h.lower() for h in header]
        for hint in CHANNEL_HEADER_HINTS:
            if hint in lower_header:
                col_idx = lower_header.index(hint)
                break
    start_row = 1 if col_idx is not None else 0
    for row in rows[start_row:]:
        if not row:
            continue
        if col_idx is not None and col_idx < len(row):
            v = (row[col_idx] or "").strip()
            if v:
                channels.append(v)
        else:
            first = next((c.strip() for c in row if c and c.strip()), "")
            if first:
                channels.append(first)
    return channels

def normalize_lines(s: str):
    return [ln.strip() for ln in s.splitlines() if ln.strip()]

def assign_pairs(channels, titles, descs, mode="titles"):
    """
    mode = "titles": số dòng = len(titles); kênh & mô tả chạy vòng.
    mode = "channels": số dòng = len(channels); tiêu đề & mô tả chạy vòng.
    """
    if not channels:
        raise ValueError("No channels found in selected CSV.")
    if not titles:
        raise ValueError("No titles provided.")

    if len(descs) <= 1:
        desc_cycle = itertools.cycle([descs[0] if descs else ""])
    else:
        desc_cycle = itertools.cycle(descs)

    if mode == "titles":
        ch_cycle = itertools.cycle(channels)
        out = []
        for i, title in enumerate(titles):
            ch = next(ch_cycle)
            d = next(desc_cycle)
            out.append((ch, title, d))
        return out
    else:  # mode == "channels"
        title_cycle = itertools.cycle(titles)
        out = []
        for ch in channels:
            t = next(title_cycle)
            d = next(desc_cycle)
            out.append((ch, t, d))
        return out

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1060x700")
        self.minsize(880, 580)

        self.group_file_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value="titles")  # "titles" (mặc định) hoặc "channels"
        self.status_var = tk.StringVar(value="Ready.")
        self._channels_cache = []
        self._last_assignments = None

        self._build_header()
        self._build_inputs()
        self._build_preview()
        self._build_footer()
        self._refresh_group_files()

    def _build_header(self):
        frm = ttk.Frame(self, padding=(10, 10, 10, 0))
        frm.pack(fill=tk.X)

        ttk.Label(frm, text="Group CSV (in ./group):").grid(row=0, column=0, sticky="w")
        self.group_combo = ttk.Combobox(frm, textvariable=self.group_file_var, state="readonly", width=48)
        self.group_combo.grid(row=0, column=1, sticky="w", padx=6)
        self.group_combo.bind("<<ComboboxSelected>>", lambda e: self._load_channels())

        ttk.Button(frm, text="Refresh", command=self._refresh_group_files).grid(row=0, column=2, padx=4)
        ttk.Button(frm, text="Open group folder", command=self._open_group_dir).grid(row=0, column=3, padx=4)

        self.channel_count_lbl = ttk.Label(frm, text="0 channels")
        self.channel_count_lbl.grid(row=0, column=4, sticky="w", padx=(12, 0))
        frm.columnconfigure(1, weight=1)

        # Distribution mode
        frm2 = ttk.Frame(self, padding=(10, 6, 10, 0))
        frm2.pack(fill=tk.X)
        ttk.Label(frm2, text="Distribution mode:").pack(side=tk.LEFT)
        ttk.Radiobutton(frm2, text="Theo tiêu đề (thiếu kênh sẽ lặp kênh)", variable=self.mode_var, value="titles").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(frm2, text="Theo kênh (mỗi kênh 1 dòng)", variable=self.mode_var, value="channels").pack(side=tk.LEFT, padx=(8, 0))

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
        ttk.Button(btns, text="Preview Distribution", command=self._preview).pack(side=tk.LEFT)
        ttk.Button(btns, text="Clear Inputs", command=self._clear_inputs).pack(side=tk.LEFT, padx=6)

    def _build_preview(self):
        frm = ttk.Frame(self, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)

        cols = ("channel", "title", "description")
        self.tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
        for col in cols:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=260 if col != "description" else 520, anchor="w")

        vsb = ttk.Scrollbar(frm, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.LEFT, fill=tk.Y)

        btns = ttk.Frame(self, padding=(10, 0, 10, 10))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Save CSV", command=self._save_csv).pack(side=tk.LEFT)
        ttk.Button(btns, text="Copy TSV", command=self._copy_tsv).pack(side=tk.LEFT, padx=6)

    def _build_footer(self):
        bar = ttk.Frame(self, relief=tk.SUNKEN, padding=6)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(bar, textvariable=self.status_var).pack(side=tk.LEFT)

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

    def _open_group_dir(self):
        if os.path.isdir(GROUPS_DIR):
            filedialog.askopenfilename(initialdir=GROUPS_DIR, title="(Read-only) group folder")
        else:
            messagebox.showwarning("Missing folder", f"'group' folder not found at:\n{GROUPS_DIR}")

    def _load_channels(self):
        name = self.group_file_var.get().strip()
        if not name:
            return
        csv_path = os.path.join(GROUPS_DIR, name)
        channels = read_channels_from_csv(csv_path)
        self._channels_cache = channels
        self.channel_count_lbl.config(text=f"{len(channels)} channels")
        self._set_status(f"Loaded {len(channels)} channels from {csv_path}")

    def _clear_inputs(self):
        self.txt_titles.delete("1.0", tk.END)
        self.txt_descs.delete("1.0", tk.END)
        self.tree.delete(*self.tree.get_children())
        self._last_assignments = None
        self._set_status("Cleared inputs & preview.")

    def _preview(self):
        group_file = self.group_file_var.get().strip()
        if not group_file:
            messagebox.showwarning("Missing CSV", "Please select a group CSV in ./group.")
            return

        titles = normalize_lines(self.txt_titles.get("1.0", tk.END))
        descs = normalize_lines(self.txt_descs.get("1.0", tk.END))
        channels = self._channels_cache
        mode = self.mode_var.get()

        try:
            assignments = assign_pairs(channels, titles, descs, mode=mode)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self.tree.delete(*self.tree.get_children())
        for ch, t, d in assignments:
            self.tree.insert("", tk.END, values=(ch, t, d))

        self._last_assignments = assignments
        if mode == "titles":
            self._set_status(f"Previewed {len(assignments)} rows (title-driven; channels cycle if needed).")
        else:
            self._set_status(f"Previewed {len(assignments)} rows (channel-driven).")

    def _save_csv(self):
        if not self._last_assignments:
            messagebox.showwarning("Nothing to save", "Click Preview first.")
            return
        base = os.path.splitext(self.group_file_var.get().strip())[0] or "group"
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"{base}__assignments_{ts}.csv"
        out_path = os.path.join(GROUPS_DIR, out_name)
        os.makedirs(GROUPS_DIR, exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["group_file", "channel", "title", "description", "mode"])
            for ch, t, d in self._last_assignments:
                w.writerow([self.group_file_var.get(), ch, t, d, self.mode_var.get()])
        self._set_status(f"Saved: {out_path}")
        messagebox.showinfo("Saved", f"Exported CSV:\n{out_path}")

    def _copy_tsv(self):
        if not self._last_assignments:
            messagebox.showwarning("Nothing to copy", "Click Preview first.")
            return
        tsv = "channel\ttitle\tdescription\n" + "\n".join(
            f"{ch}\t{t}\t{d}" for ch, t, d in self._last_assignments
        )
        self.clipboard_clear()
        self.clipboard_append(tsv)
        self._set_status("Assignments copied to clipboard as TSV.")

    def _set_status(self, msg: str):
        self.status_var.set(msg)

if __name__ == "__main__":
    app = App()
    app.mainloop()
