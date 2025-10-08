import os
import tkinter as tk
from tkinter import ttk, messagebox
import webview
import threading

DEFAULT_FOLDER = r"manage_channel\data\cleaned html"


class HTMLWebviewApp:
    def __init__(self):
        self.browser_window = None
        self.root = None
        self.folder_path = None
        self.file_list = None
        self.current_file = None

        # chạy GUI trong thread phụ
        threading.Thread(target=self.create_gui, daemon=True).start()

    def create_gui(self):
        self.root = tk.Tk()
        self.root.title("HTML Folder Previewer (Chromium)")
        self.root.geometry("1000x600")
        self.root.minsize(900, 500)

        # StringVar phải được tạo SAU khi có root
        self.folder_path = tk.StringVar(master=self.root, value=DEFAULT_FOLDER)

        self.create_widgets()
        self.load_html_files()  # Tự tải file luôn khi khởi động
        self.root.mainloop()

    def create_widgets(self):
        # --- Top bar ---
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=5)

        ttk.Label(top, text="Thư mục:").pack(side="left")
        ttk.Entry(top, textvariable=self.folder_path, width=60, state="readonly").pack(
            side="left", fill="x", expand=True, padx=5
        )
        ttk.Button(top, text="Tải danh sách", command=self.load_html_files).pack(side="left", padx=5)

        # --- Main layout ---
        body = ttk.Frame(self.root)
        body.pack(fill="both", expand=True, padx=10, pady=5)

        # Left: file list
        left_frame = ttk.Frame(body, width=250)
        left_frame.pack(side="left", fill="y")

        ttk.Label(left_frame, text="Danh sách HTML:").pack(anchor="w")
        self.file_list = tk.Listbox(left_frame)
        self.file_list.pack(fill="both", expand=True, pady=3)
        self.file_list.bind("<<ListboxSelect>>", self.on_file_select)

        # Right placeholder
        right_frame = ttk.Frame(body)
        right_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))
        ttk.Label(right_frame, text="Nội dung hiển thị trong cửa sổ Chromium riêng").pack(
            anchor="center", pady=50
        )

    def load_html_files(self):
        folder = self.folder_path.get()
        if not os.path.isdir(folder):
            messagebox.showerror("Lỗi", f"Thư mục không tồn tại:\n{folder}")
            return

        files = [f for f in os.listdir(folder) if f.lower().endswith(".html")]
        self.file_list.delete(0, tk.END)
        if not files:
            self.file_list.insert(tk.END, "(Không có file HTML)")
        else:
            for f in sorted(files):
                self.file_list.insert(tk.END, f)

    def on_file_select(self, event):
        selection = self.file_list.curselection()
        if not selection or not self.browser_window:
            return

        filename = self.file_list.get(selection[0])
        if filename.startswith("("):
            return

        file_path = os.path.join(self.folder_path.get(), filename)
        safe_path = os.path.abspath(file_path).replace("\\", "/")
        file_url = f"file:///{safe_path}"

        try:
            self.browser_window.load_url(file_url)
        except Exception as e:
            messagebox.showwarning("Cảnh báo", f"Không thể tải file: {e}")

    def run(self):
        self.browser_window = webview.create_window(
            "HTML Preview",
            html="<h3>Chưa có file được chọn</h3>",
            background_color="#FFFFFF",
        )
        webview.settings["ALLOW_DOWNLOADS"] = True
        webview.start(gui="edgechromium" if os.name == "nt" else None)


if __name__ == "__main__":
    app = HTMLWebviewApp()
    app.run()
