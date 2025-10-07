import argparse
import csv
import re
import sys
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

API_BASE = "https://www.googleapis.com/youtube/v3"

def _iso_now():
    return datetime.now(timezone.utc).isoformat()

def http_get(endpoint: str, params: Dict) -> Dict:
    url = f"{API_BASE}/{endpoint}"
    r = requests.get(url, params=params, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text}")
    return r.json()

def parse_channel_from_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Trả về (handle, channel_id, username) tùy loại URL.
    """
    # https://www.youtube.com/@Handle
    m = re.search(r"youtube\.com/@([^/?#]+)", url, re.I)
    if m:
        handle = m.group(1)
        if not handle.startswith("@"):
            handle = "@" + handle
        return handle, None, None

    # https://www.youtube.com/channel/UCxxxxxxxx
    m = re.search(r"youtube\.com/channel/(UC[0-9A-Za-z_-]{20,})", url, re.I)
    if m:
        return None, m.group(1), None

    # https://www.youtube.com/user/SomeUser
    m = re.search(r"youtube\.com/user/([^/?#]+)", url, re.I)
    if m:
        return None, None, m.group(1)

    # https://www.youtube.com/c/CustomName  (custom URL cũ) → dùng search.list để tìm channelId
    m = re.search(r"youtube\.com/c/([^/?#]+)", url, re.I)
    if m:
        return "@"+m.group(1), None, None  # thử coi như handle; nếu fail sẽ fallback search

    return None, None, None

def get_channel_resource(
    api_key: str,
    handle: Optional[str] = None,
    channel_id: Optional[str] = None,
    username: Optional[str] = None,
) -> Dict:
    """
    Lấy channel resource qua 1 trong 3 cách: forHandle / id / forUsername.
    """
    params = {
        "part": "snippet,statistics,contentDetails,brandingSettings",
        "key": api_key,
        "maxResults": 1,
    }
    endpoint = "channels"
    if handle:
        # YouTube Data API hỗ trợ forHandle (có thể để @ hoặc bỏ @)
        params["forHandle"] = handle.lstrip("@")
    elif channel_id:
        params["id"] = channel_id
    elif username:
        params["forUsername"] = username
    else:
        raise ValueError("Phải truyền handle / channel_id / username")

    data = http_get("channels", params)
    items = data.get("items", [])
    if items:
        return items[0]

    # Fallback: nếu coi custom /c/... như handle không ra, dùng search.list để tìm channel theo truy vấn
    if handle and not handle.startswith("@"):
        q = handle
    elif handle:
        q = handle.lstrip("@")
    else:
        q = username or channel_id or ""
    if not items:
        search = http_get("search", {
            "key": api_key,
            "part": "snippet",
            "q": q,
            "type": "channel",
            "maxResults": 1
        })
        sitems = search.get("items", [])
        if sitems:
            cid = sitems[0]["snippet"]["channelId"]
            return get_channel_resource(api_key, channel_id=cid)

    raise RuntimeError("Không tìm thấy kênh phù hợp.")

def get_uploads_playlist_id(channel: Dict) -> str:
    try:
        return channel["contentDetails"]["relatedPlaylists"]["uploads"]
    except KeyError:
        raise RuntimeError("Không lấy được uploads playlist ID từ channel.contentDetails.")

def list_upload_videos(api_key: str, uploads_playlist_id: str, limit: int = 50) -> List[Dict]:
    """
    Lấy danh sách video trong uploads playlist (mặc định lấy đến 'limit').
    """
    results = []
    page_token = None
    while True:
        params = {
            "key": api_key,
            "part": "snippet,contentDetails",
            "playlistId": uploads_playlist_id,
            "maxResults": min(50, max(1, limit - len(results))),
        }
        if page_token:
            params["pageToken"] = page_token
        resp = http_get("playlistItems", params)
        for it in resp.get("items", []):
            vid = {
                "videoId": it["contentDetails"]["videoId"],
                "publishedAt": it["contentDetails"].get("videoPublishedAt") or it["snippet"].get("publishedAt"),
                "title": it["snippet"]["title"],
                "description": it["snippet"].get("description", ""),
                "position": it["snippet"].get("position"),
            }
            results.append(vid)
            if len(results) >= limit:
                return results

        page_token = resp.get("nextPageToken")
        if not page_token or len(results) >= limit:
            break
        time.sleep(0.05)  # nhẹ quota

    return results

def chunked(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i+n]

def parse_iso8601_duration(duration: str) -> int:
    """
    Trả về số giây từ ISO8601 (PT#H#M#S). Đủ cho dur phổ biến của Shorts/Video.
    """
    pattern = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")
    m = pattern.fullmatch(duration)
    if not m:
        return 0
    h = int(m.group(1) or 0)
    m_ = int(m.group(2) or 0)
    s = int(m.group(3) or 0)
    return h*3600 + m_*60 + s

def get_videos_details(api_key: str, video_ids: List[str]) -> Dict[str, Dict]:
    """
    Trả về map videoId -> chi tiết (snippet, statistics, contentDetails).
    """
    out = {}
    for batch in chunked(video_ids, 50):
        resp = http_get("videos", {
            "key": api_key,
            "part": "snippet,statistics,contentDetails",
            "id": ",".join(batch)
        })
        for it in resp.get("items", []):
            vid = it["id"]
            dur = it.get("contentDetails", {}).get("duration", "")
            out[vid] = {
                "duration": dur,
                "durationSec": parse_iso8601_duration(dur),
                "viewCount": int(it.get("statistics", {}).get("viewCount", 0) or 0),
                "likeCount": int(it.get("statistics", {}).get("likeCount", 0) or 0),
                "commentCount": int(it.get("statistics", {}).get("commentCount", 0) or 0),
                "categoryId": it.get("snippet", {}).get("categoryId"),
                "tags": it.get("snippet", {}).get("tags", []),
            }
        time.sleep(0.05)
    return out

def save_csv(path: str, rows: List[Dict]):
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def main():
    ap = argparse.ArgumentParser(description="Fetch YouTube channel data (stats + latest uploads).")
    ap.add_argument("--api-key", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--handle")
    g.add_argument("--channel-id")
    g.add_argument("--username")
    g.add_argument("--url")
    ap.add_argument("--max", type=int, default=50, help="Số video muốn lấy từ uploads (tối đa 50 mỗi page).")
    ap.add_argument("--csv", help="Lưu danh sách video ra CSV nếu cung cấp đường dẫn.")
    args = ap.parse_args()

    handle = args.handle
    channel_id = args.channel_id
    username = args.username

    if args.url:
        h, cid, un = parse_channel_from_url(args.url)
        handle = handle or h
        channel_id = channel_id or cid
        username = username or un

    channel = get_channel_resource(
        api_key=args.api_key,
        handle=handle,
        channel_id=channel_id,
        username=username,
    )

    ch_stats = channel.get("statistics", {})
    ch_snip = channel.get("snippet", {})
    ch_brand = channel.get("brandingSettings", {}).get("channel", {})

    hidden = ch_stats.get("hiddenSubscriberCount", False)
    subs = None if hidden else int(ch_stats.get("subscriberCount", 0) or 0)

    print("=== Channel Info ===")
    print("Channel ID:", channel["id"])
    print("Title:", ch_snip.get("title"))
    print("Custom URL:", ch_snip.get("customUrl") or ch_brand.get("customUrl"))
    print("Published At:", ch_snip.get("publishedAt"))
    print("Country:", ch_snip.get("country"))
    print("View Count:", int(ch_stats.get("viewCount", 0) or 0))
    print("Video Count:", int(ch_stats.get("videoCount", 0) or 0))
    print("Subscriber Count:", "Hidden" if subs is None else subs)
    print()

    uploads_id = get_uploads_playlist_id(channel)
    uploads = list_upload_videos(args.api_key, uploads_id, limit=args.max)
    video_ids = [v["videoId"] for v in uploads]
    detail_map = get_videos_details(args.api_key, video_ids)

    rows = []
    for v in uploads:
        d = detail_map.get(v["videoId"], {})
        rows.append({
            "fetchedAt": _iso_now(),
            "channelId": channel["id"],
            "channelTitle": ch_snip.get("title"),
            "videoId": v["videoId"],
            "title": v["title"],
            "publishedAt": v.get("publishedAt"),
            "views": d.get("viewCount"),
            "likes": d.get("likeCount"),
            "comments": d.get("commentCount"),
            "duration": d.get("duration"),
            "durationSec": d.get("durationSec"),
            "categoryId": d.get("categoryId"),
            "tags": "|".join(d.get("tags", [])),
            "position": v.get("position"),
        })

    print(f"Fetched {len(rows)} videos.")
    if args.csv:
        save_csv(args.csv, rows)
        print(f"Saved CSV -> {args.csv}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)
