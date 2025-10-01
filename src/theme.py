import tkinter as tk
from tkinter import ttk

root = tk.Tk()
style = ttk.Style()

print(style.theme_names())   # In ra tất cả theme có sẵn
print("Theme hiện tại:", style.theme_use())
