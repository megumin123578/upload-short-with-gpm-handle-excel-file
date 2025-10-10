import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import pandas as pd
from data_crawler_module import *

def run_process():
    year = year_var.get()
    month = month_var.get()
    if not year or not month:
        messagebox.showwarning("Thiếu thông tin", "Vui lòng chọn tháng và năm!")
        return

    month_str = f"{year}-{int(month):02d}"

    try:
        # === 1. Crawl & clean dữ liệu ===
        crawl_data()
        clean_data() 

        # === 2. Chuyển link thành tên kênh cho đúng tháng ===
        df = pd.read_csv("statistics/data/orders_clean.csv", encoding="utf-8")
        replace_link_with_channel(df, month_str)

        # === 3. Hiển thị kết quả sau khi xử lý ===
        messagebox.showinfo("Hoàn tất", f"Đã xử lý dữ liệu cho tháng {month_str}")
        load_data(month_str)

    except Exception as e:
        messagebox.showerror("Lỗi", str(e))


def load_data(month_str=None):
    """Đọc CSV và hiển thị dữ liệu theo tháng đã chọn"""
    try:
        # Ưu tiên đọc file đã đổi tên kênh nếu có
        file_path = f"statistics/data/orders_with_channels_{month_str}.csv"
        if not os.path.exists(file_path):
            file_path = CLEAN_CSV_PATH

        df = pd.read_csv(file_path, encoding="utf-8-sig")
    except Exception as e:
        messagebox.showerror("Lỗi đọc file", str(e))
        return

    if "Date" not in df.columns:
        messagebox.showerror("Lỗi", "Không tìm thấy cột 'Date' trong file CSV.")
        return

    # Lọc theo tháng nếu có
    if month_str and "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        df = df[df["Date"].dt.strftime("%Y-%m") == month_str]

    # Xóa dữ liệu cũ
    for row in tree.get_children():
        tree.delete(row)

    # Thêm dữ liệu mới
    for _, row in df.iterrows():
        tree.insert("", "end", values=list(row.values))

    count_label.config(text=f"Hiển thị {len(df)} dòng dữ liệu cho {month_str}")


def on_month_year_change(event=None):
    year = year_var.get()
    month = month_var.get()
    if not year or not month:
        return
    month_str = f"{year}-{int(month):02d}"
    load_data(month_str)

root = tk.Tk()
root.title("Crawl & Xem dữ liệu theo tháng")
root.state("zoomed") 
root.minsize(850, 500)

style = ttk.Style()
style.theme_use("clam")
style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
style.configure("Treeview", rowheight=22, font=("Segoe UI", 10))
style.configure("TButton", font=("Segoe UI", 10))

#chọn tháng năm
top_frame = ttk.Frame(root, padding=10)
top_frame.pack(fill="x")

ttk.Label(top_frame, text="Chọn tháng:", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w", padx=5)
month_var = tk.StringVar(value=datetime.datetime.now().strftime("%m"))
month_cb = ttk.Combobox(top_frame, textvariable=month_var, width=5, state="readonly",
                        values=[f"{i:02d}" for i in range(1, 13)])
month_cb.grid(row=0, column=1, padx=5)

ttk.Label(top_frame, text="Chọn năm:", font=("Segoe UI", 10)).grid(row=0, column=2, sticky="w", padx=5)
year_var = tk.StringVar(value=str(datetime.datetime.now().year))
current_year = datetime.datetime.now().year
year_cb = ttk.Combobox(top_frame, textvariable=year_var, width=6, state="readonly",
                       values=[str(y) for y in range(current_year - 3, current_year + 2)])
year_cb.grid(row=0, column=3, padx=5)

ttk.Button(top_frame, text="Update dữ liệu", command=run_process).grid(row=0, column=4, padx=15)

# Gắn sự kiện thay đổi tháng/năm
month_cb.bind("<<ComboboxSelected>>", on_month_year_change)
year_cb.bind("<<ComboboxSelected>>", on_month_year_change)

# ==== Khu vực bảng ====
frame_table = ttk.Frame(root, padding=(10, 5))
frame_table.pack(expand=True, fill="both")

columns = ["ID", "Date", "Link", "Charge", "Start count", "Quantity", "Service", "Status", "Remains"]
tree = ttk.Treeview(frame_table, columns=columns, show="headings")
for col in columns:
    tree.heading(col, text=col)
    tree.column(col, width=100, anchor="w")

# Thanh cuộn ngang + dọc
scroll_y = ttk.Scrollbar(frame_table, orient="vertical", command=tree.yview)
scroll_x = ttk.Scrollbar(frame_table, orient="horizontal", command=tree.xview)
tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

scroll_y.pack(side="right", fill="y")
scroll_x.pack(side="bottom", fill="x")
tree.pack(expand=True, fill="both")

# Label đếm dòng
count_label = ttk.Label(root, text="Chưa tải dữ liệu", font=("Segoe UI", 9, "italic"), padding=5)
count_label.pack(anchor="e")

# Hiển thị dữ liệu mặc định tháng hiện tại
on_month_year_change()
root.mainloop()
