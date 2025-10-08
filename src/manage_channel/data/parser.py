from bs4 import BeautifulSoup
import csv
import os


def parse_youtube_analytics(html_path, output_csv=None):
    """Đọc file YouTube Analytics HTML và trích dữ liệu video, view, duration."""
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")
    print(len(soup.select("yta-top-performing-entities")))
    print(len(soup.select(".row")))

    # Tên channel (nếu có)
    channel_elem = soup.select_one("#entity-name")
    channel_name = channel_elem.get_text(strip=True) if channel_elem else "unknown_channel"
    channel_name = channel_name.replace(" ", "_").replace("/", "_")

    # Tìm các hàng dữ liệu video
    rows = soup.select("yta-top-performing-entities .row, yta-top-performing-entities .tappable.row")

    data = []
    for row in rows:
        title_elem = row.select_one('[id^="entity-title"]')
        duration_elem = row.select_one(".metric-cell:nth-of-type(1) > div")
        views_elem = row.select_one(".metric-cell:nth-of-type(2) > div")

        title = title_elem.get_text(strip=True) if title_elem else ""
        avg_duration = duration_elem.get_text(strip=True) if duration_elem else ""
        views = views_elem.get_text(strip=True) if views_elem else ""

        if title:
            data.append({"title": title, "avg_duration": avg_duration, "views": views})

    # Nếu không có output path → tạo tên theo channel + timestamp
    if output_csv is None:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_csv = f"{channel_name}_{timestamp}.csv"

    # Ghi ra CSV
    with open(output_csv, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "avg_duration", "views"])
        writer.writeheader()
        writer.writerows(data)

    print(f"Đã trích {len(data)} dòng từ {html_path}")
    print(f"Lưu vào: {output_csv}")

    return data


# --- Chạy trực tiếp ---
if __name__ == "__main__":
    html_file = r"manage_channel\data\html\thanh_nguyen_2025-10-08T03-21-52-761Z.html"  
    parse_youtube_analytics(html_file)
