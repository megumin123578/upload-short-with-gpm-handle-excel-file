
from datetime import datetime
import os
import shutil
from bs4 import BeautifulSoup
import os
import webview
import subprocess
REFRESH_SCRIPT = r"manage_channel\data\refresh_data.py"
FOLDER = os.path.join(os.path.expanduser("~"), "Downloads")
LEGIT_FILENAME = ["audience","content","overview"]
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_HTML_DIR = f'{BASE_DIR}/data/html'
OUTPUT_CLEANED_HTML_DIR = f'{BASE_DIR}/data/cleaned html'


print(OUTPUT_HTML_DIR)

def list_html_paths(folder):
    html_files = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".html")
    ]
    return html_files

def move_file_to_html_folder(ls, dir=OUTPUT_HTML_DIR):
    # create folder if not exist
    os.makedirs(dir, exist_ok=True)

    # delete all file in html folder
    for filename in os.listdir(dir):
        path = os.path.join(dir, filename)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Can't delete {path}: {e}")

    # move file from ls to html folder
    for src in ls:
        if not os.path.isfile(src):
            print(f"Skip: {src} (non exist or not file)")
            continue

        dest = os.path.join(dir, os.path.basename(src))
        try:
            shutil.move(src, dest)
            print(f"Moved: {src} → {dest}")
        except Exception as e:
            print(f"Error when move {src}: {e}")



def delete_unwanted_files(files):
    today = datetime.today().strftime("%Y-%m-%d")
    deleted = []

    for file in files:
        # lấy tên file (không gồm thư mục)
        filename = os.path.basename(file)
        count = 0
        for legit in LEGIT_FILENAME: #check đuôi file
            if legit not in filename:
                count += 1
        if count == 3:
            try:
                os.remove(file)
                deleted.append(file)
                print(f"Deleted: {file}")
            except Exception as e:
                print(f"Error when deleted {file}: {e}")

        #update lại list
    remaining_files = list_html_paths(FOLDER)
    for file in remaining_files:
        filename = os.path.basename(file)
        if not filename.startswith(today): #check đầu file chứa data ngày hôm nay
            try:
                os.remove(file)
                deleted.append(file)
                print(f"Deleted: {file}")
            except Exception as e:
                print(f"Error when deleted {file}: {e}")

    print(f"\nCompleted. Deleted {len(deleted)} file, keep file has {today} in name.")
    print(f'Remaining files: ')
    for file in list_html_paths(FOLDER):
        print("•", file)

    return list_html_paths(FOLDER)


from concurrent.futures import ThreadPoolExecutor, as_completed

def clean_html_file(file, output_dir):
    try:
        base = os.path.basename(file)
        parts = base.split("_")
        if len(parts) < 3:
            return f"Wrong name format: {base}"

        date = parts[0]
        name_channel = "_".join(parts[1:-1])
        tab_part = parts[-1]
        tab = tab_part.replace(".html", "")

        date_tab_dir = os.path.join(output_dir, date, tab)
        os.makedirs(date_tab_dir, exist_ok=True)

        # đọc file
        with open(file, 'r', encoding='utf-8') as f:
            html = f.read()

        # parse & làm sạch
        soup = BeautifulSoup(html, 'lxml')
        for tag in soup.find_all(["header", "ytcp-navigation-drawer", "ytcp-primary-action-bar", "script"]):
            tag.decompose()

        head = soup.find("head")
        if head and not head.find("meta", attrs={"charset": True}):
            meta = soup.new_tag("meta", charset="utf-8")
            head.insert(0, meta)

        # lưu file
        save_path = os.path.join(date_tab_dir, f"{name_channel}.html")
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(str(soup))

        return f"Saved: {save_path}"
    
    except Exception as e:
        return f"Error when handling {file}: {e}"
    
    


def remove_abundant_value(ls, output_dir=OUTPUT_CLEANED_HTML_DIR, max_workers=8):
    ls = [file for file in ls if os.path.isfile(file)]
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(clean_html_file, file, output_dir): file for file in ls}
        for future in as_completed(futures):
            print(future.result())

    print("!!DONE!!")
    print("!!SUCCESFULLY!!")


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
            width: 15%;
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
        #reloadBtn:hover { background: #005a9e; }
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
            transition: background 0.15s;
        }
        a:hover { background: #e6f0ff; }
        a.active {
            background: #0078d7;
            color: white;
            font-weight: bold;
        }
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
        const htmlCache = {}; // 🔥 cache tạm ở JS

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

        // Khi chọn mục → load danh sách file
        async function loadFiles() {
            const tab = document.getElementById('tabSelect').value;
            currentTab = tab;
            const list = document.getElementById('fileList');

            // 🧠 Skip re-render nếu date+tab trùng
            if (list.dataset.lastKey === currentDate + "_" + currentTab) {
                console.log("Danh sách không đổi, bỏ qua render lại");
                return;
            }
            list.dataset.lastKey = currentDate + "_" + currentTab;

            const files = await window.pywebview.api.list_files(currentDate, currentTab);
            list.innerHTML = files.map(f => {
                const name = f.replace(/\\.html$/i, "");
                return `<li><a href='#' onclick='loadFile("${f}")'>${name}</a></li>`;
            }).join('');

            if (files.length > 0) loadFile(files[0]);
            else {
                document.getElementById('iframeViewer').srcdoc =
                    "<h3 style='text-align:center;margin-top:40px;color:gray;'>Không có file nào</h3>";
                document.getElementById('filenameLabel').innerText = `${currentDate} / ${currentTab}`;
            }
        }

        // Khi click chọn kênh (hoặc load tự động)
        async function loadFile(name) {
            if (!name) return;
            const cleanName = name.replace(/\\.html$/i, "");
            document.getElementById('filenameLabel').innerText =
                `${currentDate} / ${currentTab} / ${cleanName}`;

            const iframe = document.getElementById('iframeViewer');
            iframe.srcdoc = "<h3 style='text-align:center;margin-top:40px;color:gray;'>Đang tải...</h3>";

            const cacheKey = currentDate + "_" + currentTab + "_" + name;
            let html;

            // ⚡ Lấy từ cache nếu có
            if (htmlCache[cacheKey]) {
                html = htmlCache[cacheKey];
            } else {
                html = await window.pywebview.api.load_html(currentDate, currentTab, name);
                htmlCache[cacheKey] = html; // lưu cache
            }

            iframe.srcdoc = html;

            // highlight link đang chọn
            const links = document.querySelectorAll('#fileList a');
            links.forEach(link => link.classList.remove('active'));
            const activeLink = [...links].find(link => link.textContent === cleanName);
            if (activeLink) activeLink.classList.add('active');
        }

        // Nút refresh
        async function runRefresh() {
            const iframe = document.getElementById('iframeViewer');
            iframe.srcdoc = "<h3 style='color:gray;text-align:center;margin-top:40px;'>Đang xử lý, xin hãy đợi tí...</h3>";
            const result = await window.pywebview.api.run_refresh_script();
            iframe.srcdoc = result;
        }

        // Khởi tạo: tự động chọn ngày mới nhất + mục overview
        window.addEventListener("pywebviewready", async () => {
            const dates = await window.pywebview.api.list_dates();
            const sel = document.getElementById('dateSelect');
            sel.innerHTML = "<option value=''>-- Chọn ngày --</option>" +
                dates.map(d => `<option value='${d}'>${d}</option>`).join('');

            if (dates.length > 0) {
                const newest = dates[0];
                sel.value = newest;
                currentDate = newest;

                const tabs = await window.pywebview.api.list_tabs(newest);
                const tabSel = document.getElementById('tabSelect');
                tabSel.innerHTML = "<option value=''>-- Chọn mục --</option>" +
                    tabs.map(t => `<option value='${t}'>${t}</option>`).join('');

                const defaultTab = tabs.includes("overview") ? "overview" : tabs[0];
                tabSel.value = defaultTab;
                currentTab = defaultTab;

                const files = await window.pywebview.api.list_files(newest, defaultTab);
                const list = document.getElementById('fileList');
                list.innerHTML = files.map(f => {
                    const name = f.replace(/\\.html$/i, "");
                    return `<li><a href='#' onclick='loadFile("${f}")'>${name}</a></li>`;
                }).join('');

                if (files.length > 0) loadFile(files[0]);
                else {
                    document.getElementById('iframeViewer').srcdoc =
                        "<h3 style='text-align:center;margin-top:40px;color:gray;'>Không có file nào</h3>";
                    document.getElementById('filenameLabel').innerText = `${newest} / ${defaultTab}`;
                }
            }
        });
        </script>
    </body>
    </html>
    """
    return html
