from bs4 import BeautifulSoup

def keep_content_div(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "lxml")

    #delete header
    for header in soup.find_all("header", class_="ytcpAppHeaderHeader"):
        header.decompose()

    for drawer in soup.find_all("ytcp-navigation-drawer"):
        drawer.decompose()

    for actionbar in soup.find_all("ytcp-primary-action-bar"):
        actionbar.decompose()

    for script in soup.find_all("script"):
        script.decompose()
    
    head = soup.find("head")
    if head and not head.find("meta", attrs={"charset": True}):
        meta = soup.new_tag("meta", charset="utf-8")
        head.insert(0, meta)


    with open(output_path, "w", encoding="utf-8") as f:
        f.write(str(soup))

# Ví dụ dùng
if __name__ == "__main__":
    keep_content_div(
        r"manage_channel\data\html\thanh_nguyen_2025-10-08T08-26-58-518Z.html",
        r"manage_channel\data\html\youtube_analytics_clean.html"
    )
    print("manage_channel\data\html\youtube_analytics_clean.html")