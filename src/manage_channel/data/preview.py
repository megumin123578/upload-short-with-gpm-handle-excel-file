import os
import subprocess
import webview
from data_helper import *

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_DIR = os.path.join(BASE_DIR, "cleaned html")

class API:
    def __init__(self, folder):
        self.folder = folder

    def list_dates(self):
        """Trả về danh sách thư mục ngày"""
        try:
            dates = [
                d for d in os.listdir(self.folder)
                if os.path.isdir(os.path.join(self.folder, d))
            ]
            dates.sort(reverse=True)
            return dates
        except Exception as e:
            return [f"Lỗi: {e}"]

    def list_tabs(self, date_folder):
        """Trả về các thư mục con trong ngày (audience, content, overview)"""
        path = os.path.join(self.folder, date_folder)
        try:
            tabs = [
                d for d in os.listdir(path)
                if os.path.isdir(os.path.join(path, d))
            ]
            return sorted(tabs)
        except Exception:
            return []

    def list_files(self, date_folder, tab):
        """Trả về danh sách file HTML trong thư mục ngày/tab"""
        path = os.path.join(self.folder, date_folder, tab)
        try:
            return [
                f for f in os.listdir(path)
                if f.lower().endswith(".html")
            ]
        except Exception:
            return []

    def load_html(self, date_folder, tab, filename):
        """Đọc nội dung file"""
        file_path = os.path.join(self.folder, date_folder, tab, filename)
        if not os.path.isfile(file_path):
            return "<h3 style='color:red'>Không tìm thấy file</h3>"
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"<h3 style='color:red'>Lỗi đọc file: {e}</h3>"

    def run_refresh_script(self):
        """Chạy file Python khác khi ấn nút Refresh"""
        try:
            result = subprocess.run(
                ["python", REFRESH_SCRIPT],
                capture_output=True,
                text=True,
                check=True
            )
            return f"<pre style='color:green'>Đã chạy xong:\n{result.stdout}</pre>"
        except subprocess.CalledProcessError as e:
            return f"<pre style='color:red'>Lỗi:\n{e.stderr}</pre>"
        except Exception as e:
            return f"<pre style='color:red'>Lỗi không xác định: {e}</pre>"

def generate_index_html():
    html = """
    <html>
    <head>
    <meta charset='utf-8'>
    <title>HTML Folder Viewer</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            display: flex;
            height: 100vh;
            margin: 0;
            overflow: hidden;
        }
        #sidebar {
            width: 25%;
            background: #f3f3f3;
            overflow-y: auto;
            padding: 10px;
            border-right: 1px solid #ccc;
        }
        #viewer {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        #viewer-header {
            background: #fafafa;
            border-bottom: 1px solid #ddd;
            padding: 10px 12px;
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }
        #filenameLabel {
            font-weight: bold;
            color: #333;
            margin-right: auto;
        }
        select, button {
            padding: 5px 8px;
            font-size: 14px;
        }
        #reloadBtn {
            background: #0078d7;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 6px 10px;
            cursor: pointer;
        }
        #reloadBtn:hover {
            background: #005a9e;
        }
        iframe {
            flex: 1;
            width: 100%;
            border: none;
            background: white;
        }
        ul { list-style: none; padding: 0; margin: 0; }
        li { margin: 4px 0; }
        a {
            text-decoration: none;
            color: #0078d7;
            display: block;
            padding: 6px 8px;
            border-radius: 4px;
            font-size: 15px;
        }
        a:hover { background: #e6f0ff; }
    </style>
    </head>
    <body>
        <div id="sidebar">
            <h3>Danh sách kênh</h3>
            <ul id="fileList"></ul>
        </div>

        <div id="viewer">
            <div id="viewer-header">
                <span id="filenameLabel">Chưa chọn kênh</span>

                <label>Ngày:</label>
                <select id="dateSelect" onchange="loadTabs()">
                    <option value="">-- Chọn ngày --</option>
                </select>

                <label>Mục:</label>
                <select id="tabSelect" onchange="loadFiles()">
                    <option value="">-- Chọn mục --</option>
                </select>

                <button id="reloadBtn" onclick="runRefresh()">Refresh</button>
            </div>

            <iframe id="iframeViewer" srcdoc="<h3 style='text-align:center;margin-top:40px;'>Chọn một file để xem nội dung</h3>"></iframe>
        </div>

        <script>
        let currentDate = "";
        let currentTab = "";
        let currentFile = "";

        async function initDates() {
            const dates = await window.pywebview.api.list_dates();
            const sel = document.getElementById('dateSelect');
            sel.innerHTML = "<option value=''>-- Chọn ngày --</option>" +
                dates.map(d => `<option value='${d}'>${d}</option>`).join('');
        }

        // Khi chọn ngày → load danh sách mục
        async function loadTabs() {
            const date = document.getElementById('dateSelect').value;
            currentDate = date;
            const tabs = await window.pywebview.api.list_tabs(date);
            const sel = document.getElementById('tabSelect');
            sel.innerHTML = "<option value=''>-- Chọn mục --</option>" +
                tabs.map(t => `<option value='${t}'>${t}</option>`).join('');
            document.getElementById('fileList').innerHTML = "";
        }

        // Khi chọn mục → load danh sách file và tự động mở file đầu tiên
        async function loadFiles() {
            const tab = document.getElementById('tabSelect').value;
            currentTab = tab;
            const files = await window.pywebview.api.list_files(currentDate, currentTab);
            const list = document.getElementById('fileList');

            // hiển thị tên file không có đuôi .html
            list.innerHTML = files.map(f => {
                const name = f.replace(/\.html$/i, "");
                return `<li><a href='#' onclick='loadFile("${f}")'>${name}</a></li>`;
            }).join('');

            // tự động load file đầu tiên nếu có
            if (files.length > 0) {
                loadFile(files[0]);
            } else {
                document.getElementById('iframeViewer').srcdoc =
                    "<h3 style='text-align:center;margin-top:40px;color:gray;'>Không có file nào</h3>";
                document.getElementById('filenameLabel').innerText = `${currentDate} / ${currentTab}`;
            }
        }

        // Khi click chọn kênh (hoặc load tự động)
        async function loadFile(name) {
            const html = await window.pywebview.api.load_html(currentDate, currentTab, name);
            currentFile = name;
            const cleanName = name.replace(/\.html$/i, "");
            document.getElementById('filenameLabel').innerText =
                `${currentDate} / ${currentTab} / ${cleanName}`;
            document.getElementById('iframeViewer').srcdoc = html;
        }

        // Nút refresh
        async function runRefresh() {
            const iframe = document.getElementById('iframeViewer');
            iframe.srcdoc = "<h3 style='color:gray;text-align:center;margin-top:40px;'>Đang chạy refresh_data.py...</h3>";
            const result = await window.pywebview.api.run_refresh_script();
            iframe.srcdoc = result;
        }

        // Gọi init sau khi pywebview sẵn sàng
        window.addEventListener("pywebviewready", initDates);
        </script>

    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    api = API(MAIN_DIR)
    html = generate_index_html()

    webview.create_window(
        "HTML Folder Viewer",
        html=html,
        js_api=api,
        width=1700,
        height=1000,
        resizable=True,
    )
    webview.start(gui="edgechromium" if os.name == "nt" else None)
