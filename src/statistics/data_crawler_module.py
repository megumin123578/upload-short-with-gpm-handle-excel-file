import requests, re
import requests
from bs4 import BeautifulSoup
import csv
import os
import pandas as pd

CSV_PATH = r"statistics\data\orders_all.csv"
CLEAN_CSV_PATH = r"statistics\data\orders_clean.csv"
session = requests.Session()
cookies = {
    "PHPSESSID": "hp4055kjcj3po9pon4qv5sonlt",
}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://smmstore.pro/api",
}
#read older csv
existing_ids = set()

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
        return "Unidentified"


def crawl_data(csv_path=CSV_PATH):
    if os.path.exists(csv_path):
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    existing_ids.add(row[0].strip())
        print(f"Đã tải {len(existing_ids)} ID cũ từ {csv_path}")

    all_rows = []
    page = 1
    stop_flag = False

    while not stop_flag:
        url = f"https://smmstore.pro/orders?page={page}"
        print("Crawling:", url)
        r = session.get(url, headers=headers, cookies=cookies)
        soup = BeautifulSoup(r.text, "html.parser")
        table = soup.find("table")

        if not table:
            print("Không tìm thấy bảng — có thể hết trang hoặc cookie hết hạn.")
            break

        rows = table.find_all("tr")[1:]
        num_rows = len(rows)
        if num_rows == 0:
            print(f"Hết dữ liệu sau trang {page}")
            break

        for tr in rows:
            cols = [td.get_text(strip=True) for td in tr.find_all("td")]
            if not cols:
                continue

            # ✅ Bỏ cột rỗng ở cuối (ngăn sinh dấu phẩy thừa)
            while cols and cols[-1] == "":
                cols.pop()

            order_id = cols[0]
            if order_id in existing_ids:
                print(f"Phát hiện ID {order_id} đã tồn tại trong CSV — dừng crawler.")
                stop_flag = True
                break

            existing_ids.add(order_id)
            all_rows.append(cols)

        if stop_flag:
            break

        print(f"Lấy được {num_rows} hàng từ trang {page}")

        if num_rows < 100:
            print(f"Hết dữ liệu ở trang {page} (chỉ có {num_rows} hàng)")
            break

        page += 1

    if all_rows:
        headers_list = ["ID", "Date", "Link", "Charge", "Start count",
                        "Quantity", "Service", "Status", "Remains"]

        file_exists = os.path.exists(csv_path)
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists or os.stat(csv_path).st_size == 0:
                writer.writerow(headers_list)
            writer.writerows(all_rows)

        print(f"Đã ghi thêm {len(all_rows)} đơn hàng mới vào {csv_path}")
    else:
        print("Không có đơn mới để ghi.")

    print(f"Tổng cộng hiện có {len(existing_ids)} đơn hàng trong file CSV.")



def pre_process_data(file):
    df = pd.read_csv(file, index_col=False, sep=None, engine='python')
    filtered_df = df[["Date", "Link", "Charge"]].dropna(subset=["Date", "Link", "Charge"])
    return filtered_df


def clean_data(input_path = "statistics\data\orders_all.csv", output_path="statistics\data\orders_clean.csv", expected_cols = 9 ):
    with open(input_path, encoding="utf-8-sig") as infile, \
        open(output_path, "w", encoding="utf-8-sig", newline="") as outfile:

        reader = csv.reader(infile)
        writer = csv.writer(outfile)

        for i, row in enumerate(reader, start=1):
            if len(row) == expected_cols:
                writer.writerow(row)
            elif len(row) > expected_cols:
                # keep 9 cols
                writer.writerow(row[:expected_cols])
                print(f"Dòng {i}: có {len(row)} cột, đã cắt bớt còn {expected_cols}.")
            else:
                # skip
                print(f"Dòng {i}: chỉ có {len(row)} cột, đã bỏ qua.")

    print(f"Đã làm sạch file, lưu tại: {output_path}")

import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

def replace_link_with_channel(df, month, max_workers=10):
    df = df.copy()
    output_file = f"statistics/data/orders_with_channels_{month}.csv"

    # === 1. Xử lý cột ngày ===
    date_col = next((c for c in df.columns if 'date' in c.lower()), None)
    if not date_col:
        raise KeyError("Không tìm thấy cột chứa 'date' trong CSV!")
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    df = df[df[date_col].dt.strftime("%Y-%m") == month]

    # === 2. Lấy danh sách URL duy nhất ===
    unique_links = df["Link"].dropna().unique().tolist()
    print(f"🔗 Có {len(unique_links)} đường dẫn cần xử lý...")

    cache = {}

    def fetch_channel(url):
        """Gọi url_to_channel 1 lần, có kiểm tra cache"""
        if url in cache:
            return url, cache[url]
        try:
            channel = url_to_channel(url)
            cache[url] = channel
            return url, channel
        except Exception as e:
            print(f"Lỗi khi xử lý {url}: {e}")
            return url, None

    # === 3. Dùng ThreadPool để chạy song song ===
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_channel, url): url for url in unique_links}
        for i, future in enumerate(as_completed(futures), 1):
            url, channel = future.result()
            print(f"[{i}/{len(unique_links)}] {url} → {channel}")

    # === 4. Gán kết quả lại cho DataFrame ===
    df["Link"] = df["Link"].map(cache).fillna(df["Link"])

    df.to_csv(output_file, index=False, encoding="utf-8")
    print(f"Đã xử lý {len(df)} dòng trong tháng {month}, lưu tại: {output_file}")
    return df
