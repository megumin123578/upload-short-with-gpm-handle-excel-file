
from datetime import datetime
import os
import shutil
from bs4 import BeautifulSoup

FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
LEGIT_FILENAME = ["audience","content","overview"]
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_HTML_DIR = f'{BASE_DIR}/data/html'
OUTPUT_CLEANED_HTML_DIR = f'{BASE_DIR}/data/cleaned html'


print(OUTPUT_HTML_DIR)

def list_html_paths(folder):
    html_files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".html")
    ]
    return html_files

def move_file_to_html_folder(ls, dir=OUTPUT_HTML_DIR):
    # create folder if not exist
    os.makedirs(dir, exist_ok=True)

    # delete all file in html folder
    for filename in os.listdir(dir):
        path = os.path.join(dir, filename)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Không thể xóa {path}: {e}")

    # move file from ls to html folder
    for src in ls:
        if not os.path.isfile(src):
            print(f"Bỏ qua: {src} (không tồn tại hoặc không phải file)")
            continue

        dest = os.path.join(dir, os.path.basename(src))
        try:
            shutil.move(src, dest)
            print(f"Đã chuyển: {src} → {dest}")
        except Exception as e:
            print(f"Lỗi khi chuyển {src}: {e}")



def delete_unwanted_files(files):
    today = datetime.today().strftime("%Y-%m-%d")
    deleted = []

    for file in files:
        # lấy tên file (không gồm thư mục)
        filename = os.path.basename(file)
        count = 0
        for legit in LEGIT_FILENAME: #check đuôi file
            if legit not in filename:
                count += 1
        if count == 3:
            try:
                os.remove(file)
                deleted.append(file)
                print(f"Deleted: {file}")
            except Exception as e:
                print(f"Error when deleted {file}: {e}")

        #update lại list
    remaining_files = list_html_paths(FOLDER)
    for file in remaining_files:
        filename = os.path.basename(file)
        if not filename.startswith(today): #check đầu file chứa data ngày hôm nay
            try:
                os.remove(file)
                deleted.append(file)
                print(f"Deleted: {file}")
            except Exception as e:
                print(f"Error when deleted {file}: {e}")

    print(f"\nCompleted. Deleted {len(deleted)} file, keep file has {today} in name.")
    print(f'Remaining files: ')
    for file in list_html_paths(FOLDER):
        print("•", file)

    return list_html_paths(FOLDER)


from concurrent.futures import ThreadPoolExecutor, as_completed

def clean_html_file(file, output_dir):
    try:
        base = os.path.basename(file)
        parts = base.split("_")
        if len(parts) < 3:
            return f"Wrong name format: {base}"

        date = parts[0]
        name_channel = "_".join(parts[1:-1])
        tab_part = parts[-1]
        tab = tab_part.replace(".html", "")

        date_tab_dir = os.path.join(output_dir, date, tab)
        os.makedirs(date_tab_dir, exist_ok=True)

        # đọc file
        with open(file, 'r', encoding='utf-8') as f:
            html = f.read()

        # parse & làm sạch
        soup = BeautifulSoup(html, 'lxml')
        for tag in soup.find_all(["header", "ytcp-navigation-drawer", "ytcp-primary-action-bar", "script"]):
            tag.decompose()

        head = soup.find("head")
        if head and not head.find("meta", attrs={"charset": True}):
            meta = soup.new_tag("meta", charset="utf-8")
            head.insert(0, meta)

        # lưu file
        save_path = os.path.join(date_tab_dir, f"{name_channel}.html")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(str(soup))

        return f"Saved: {save_path}"

    except Exception as e:
        return f"Error when handling {file}: {e}"


def remove_abundant_value(ls, output_dir=OUTPUT_CLEANED_HTML_DIR, max_workers=8):
    ls = [file for file in ls if os.path.isfile(file)]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(clean_html_file, file, output_dir): file for file in ls}
        for future in as_completed(futures):
            print(future.result())


