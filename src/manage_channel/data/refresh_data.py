
from data_helper import *
if __name__ == "__main__":
    html_paths = list_html_paths(FOLDER)
    print(f"Found {len(html_paths)} file HTML.")
    for path in html_paths:
        print("•", path)
    list_html_after_delete = delete_unwanted_files(html_paths)
    #move to html folder
    if len(list_html_after_delete) > 0:
        html_new_dirs = move_file_to_html_folder(list_html_after_delete)
    else:
        print("No files to process")