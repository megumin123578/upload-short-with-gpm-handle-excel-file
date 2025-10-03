import requests
import json

url = "https://raw.githubusercontent.com/megumin123578/upload-short-with-gpm-handle-excel-file/main/manifest.json"
r = requests.get(url)
print("Content-Type:", r.headers.get("content-type"))
print("Text:", r.text[:200])  

data = json.loads(r.text)  
