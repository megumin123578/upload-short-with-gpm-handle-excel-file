import requests, re

url = "https://youtu.be/ERJ_diPCMYQ"
html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text

match = re.search(r'"ownerChannelName":"(.*?)"', html)
if match:
    print("Kênh:", match.group(1))
