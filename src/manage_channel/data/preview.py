import os
import webview
import subprocess

DEFAULT_FOLDER = r"manage_channel\data\cleaned html\Channel analytics"
REFRESH_SCRIPT = r"manage_channel\data\refresh_data.py"

class API:
    def __init__(self, folder):
        self.folder = folder

    def load_html(self, filename):
        """Đọc nội dung file và trả về dạng text"""
        file_path = os.path.abspath(os.path.join(self.folder, filename))
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


def generate_index_html(files):
    """Giao diện danh sách + khung hiển thị (giữ sidebar + viewer cố định)"""
    list_items = "".join(
        f"<li><a href='#' onclick='loadFile(\"{f}\")'>{f}</a></li>" for f in files
    )

    html = f"""
    <html>
    <head>
    <meta charset='utf-8'>
    <title>HTML Folder Viewer</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            display: flex;
            height: 100vh;
            margin: 0;
            overflow: hidden;
        }}
        #list {{
            width: 25%;
            background: #f3f3f3;
            overflow-y: auto;
            padding: 10px;
            border-right: 1px solid #ccc;
        }}
        #viewer {{
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        #viewer-header {{
            background: #fafafa;
            border-bottom: 1px solid #ddd;
            padding: 10px 12px;
            font-size: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        #filenameLabel {{
            font-weight: bold;
            color: #333;
        }}
        #reloadBtn {{
            background: #0078d7;
            color: white;
            border: none;
            border-radius: 5px;
            padding: 6px 10px;
            cursor: pointer;
        }}
        #reloadBtn:hover {{
            background: #005a9e;
        }}
        iframe {{
            flex: 1;
            width: 100%;
            border: none;
            background: white;
        }}
        li {{ margin: 4px 0; }}
        a {{
            text-decoration: none;
            color: #0078d7;
            display: block;
            padding: 6px 8px;
            border-radius: 4px;
            font-size: 15px;
        }}
        a:hover {{
            background: #e6f0ff;
        }}
        h3 {{
            margin-top: 0;
        }}
    </style>
    </head>
    <body>
        <div id="list">
            <h3>Danh sách kênh</h3>
            <ul>{list_items}</ul>
        </div>

        <div id="viewer">
            <div id="viewer-header">
                <span id="filenameLabel">Chưa chọn kênh</span>
                <button id="reloadBtn" onclick="runRefresh()">Refresh</button>
            </div>
            <iframe id="iframeViewer" srcdoc="<h3 style='text-align:center;margin-top:40px;'>Chọn một file để xem nội dung</h3>"></iframe>
        </div>

        <script>
        let currentFile = null;

        async function loadFile(name) {{
            const html = await window.pywebview.api.load_html(name);
            currentFile = name;
            document.getElementById('filenameLabel').innerText = name;
            const iframe = document.getElementById('iframeViewer');
            iframe.srcdoc = html;
        }}

        async function reloadCurrent() {{
            if (currentFile) {{
                loadFile(currentFile);
            }}
        }}

        async function runRefresh() {{
            const iframe = document.getElementById('iframeViewer');
            iframe.srcdoc = "<h3 style='color:gray;text-align:center;margin-top:40px;'>Đang chạy refresh_data.py...</h3>";
            const result = await window.pywebview.api.run_refresh_script();
            iframe.srcdoc = result;
        }}



        </script>
    </body>
    </html>
    """
    return html


if __name__ == "__main__":
    files = sorted(
        [f for f in os.listdir(DEFAULT_FOLDER) if f.lower().endswith(".html")]
    )
    api = API(DEFAULT_FOLDER)
    html = generate_index_html(files)
    
    webview.create_window(
        "HTML Folder Viewer",
        html=html,
        js_api=api,
        width=1700,
        height=1000,
        resizable=True,
    )
    webview.start(gui="edgechromium" if os.name == "nt" else None)
