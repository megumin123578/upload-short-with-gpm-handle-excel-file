import os

APP_TITLE = "AUTO GENERATE UPLOAD SHORT YOUTUBE"


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # lấy thư mục gốc
GROUPS_DIR = os.path.join(BASE_DIR, "group")
OUTPUT_DIR = os.path.join(BASE_DIR, "upload")
EXCEL_DIR = os.path.join(BASE_DIR, "upload_data.xlsx")


CHANNEL_HEADER_HINTS = [
    "channel", "kênh", "kenh", "channel_id", "channel name", "channel_name", "name", "id"
]


