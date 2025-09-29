
import tkinter as tk
from tkinter import messagebox

# Store pairs
pairs = []

def add_pair():
    title = title_entry.get().strip()
    description = desc_entry.get().strip()
    if not title or not description:
        messagebox.showerror("Input Error", "Both title and description are required.")
        return
    pairs.append((title, description))
    update_output()
    title_entry.delete(0, tk.END)
    desc_entry.delete(0, tk.END)

def update_output():
    output_area.config(state=tk.NORMAL)
    output_area.delete("1.0", tk.END)
    for idx, (title, desc) in enumerate(pairs, 1):
        output_area.insert(tk.END, f"{idx}. Title: {title}\n   Description: {desc}\n\n")
    output_area.config(state=tk.DISABLED)

# Set up GUI
root = tk.Tk()
root.title("Title & Description Input")

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

title_label = tk.Label(frame, text="Title:")
title_label.grid(row=0, column=0, sticky="e")
title_entry = tk.Entry(frame, width=40)
title_entry.grid(row=0, column=1, padx=5, pady=5)

desc_label = tk.Label(frame, text="Description:")
desc_label.grid(row=1, column=0, sticky="e")
desc_entry = tk.Entry(frame, width=40)
desc_entry.grid(row=1, column=1, padx=5, pady=5)

add_btn = tk.Button(frame, text="Add Pair", command=add_pair)
add_btn.grid(row=2, column=0, columnspan=2, pady=5)

output_label = tk.Label(frame, text="Added Pairs:")
output_label.grid(row=3, column=0, columnspan=2)

output_area = tk.Text(frame, height=10, width=50, state=tk.DISABLED)
output_area.grid(row=4, column=0, columnspan=2, pady=5)

root.mainloop()
