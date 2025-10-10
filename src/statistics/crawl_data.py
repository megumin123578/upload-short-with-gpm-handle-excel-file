import requests
from bs4 import BeautifulSoup
import csv

session = requests.Session()

cookies = {
    "PHPSESSID": "hp4055kjcj3po9pon4qv5sonlt",  # thay cookie mới khi hết hạn
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://smmstore.pro/api",
}

all_rows = []
page = 1
last_first_id = None  # để so sánh trùng

while True:
    url = f"https://smmstore.pro/orders?page={page}"
    print("Crawling:", url)
    r = session.get(url, headers=headers, cookies=cookies)

    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table:
        print("Không tìm thấy bảng — có thể hết trang hoặc cookie hết hạn.")
        break

    rows = table.find_all("tr")[1:]  # bỏ header
    num_rows = len(rows)
    if num_rows == 0:
        print(f"Hết dữ liệu sau trang {page}")
        break

    first_id = rows[0].find_all("td")[0].get_text(strip=True)

    if first_id == last_first_id:
        print(f"Phát hiện trùng dữ liệu ở trang {page}, dừng crawler.")
        break

    last_first_id = first_id

    for tr in rows:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        all_rows.append(cols)

    print(f"Lấy được {num_rows} hàng từ trang {page}")

    # Nếu trang có ít hơn 100 hàng thì coi như trang cuối
    if num_rows < 100:
        print(f"Hết dữ liệu ở trang {page} (chỉ có {num_rows} hàng)")
        break

    page += 1

# Lưu CSV
with open("statistics\orders_all.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(all_rows)

print(f"Hoàn tất! Tổng cộng lấy được {len(all_rows)} đơn hàng.")
