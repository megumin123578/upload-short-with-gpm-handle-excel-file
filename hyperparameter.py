import os

APP_TITLE = "Distribute Titles to Channels (group/*.csv)"
GROUPS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "group")

CHANNEL_HEADER_HINTS = [
    "channel", "kênh", "kenh", "channel_id", "channel name", "channel_name", "name", "id"
]

OUTPUT_DIR = r"E:\auto upload with gpm\upload" 

HAS_TKCAL = True