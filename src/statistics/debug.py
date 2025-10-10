from data_crawler_module import *
import requests, re


API_KEY = "AIzaSyDwWltIR-XP9V61V7RNTTz-G04mVfHKlsQ"

def url_to_channel(url: str):
    # Lấy video_id từ URL
    match = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
    if not match:
        return None
    video_id = match.group(1)

    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={API_KEY}"
    r = requests.get(api_url)
    data = r.json()

    if "items" in data and data["items"]:
        return data["items"][0]["snippet"]["channelTitle"]
    else:
        return "Không tìm thấy kênh"

print(url_to_channel('https://youtu.be/ERJ_diPCMYQ'))
