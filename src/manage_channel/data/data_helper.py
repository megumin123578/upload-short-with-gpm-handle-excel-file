
from datetime import datetime
import os
FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
LEGIT_FILENAME = ["audience","content","overview"]

def list_html_paths(folder):
    html_files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".html")
    ]
    return html_files

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
 
#move file to correct location