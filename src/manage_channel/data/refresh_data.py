
from data_helper import *
if __name__ == "__main__":
    html_paths = list_html_paths(FOLDER)
    print(f"Found {len(html_paths)} file HTML.")
    for path in html_paths:
        print("•", path)
    delete_unwanted_files(html_paths)
