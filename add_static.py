# Append static file serving to web_app.py
import os

base = "C:\\Users\\diorl\\.cline\\data\\workspaces\\chat\\agent-1c-demo"
web_app_path = os.path.join(base, "agent", "web_app.py")

with open(web_app_path, "r", encoding="utf-8") as f:
    content = f.read()

if "serve_static" in content:
    print("Static serving already exists")
else:
    static_code = """
# ==================== Статические файлы ====================

STATIC_DIR = Path(__file__).resolve().parent


class StaticHandler:
    @staticmethod
    def get_static_file(path):
        \"\"\"Отдать статический файл: HTML, CSS, JS\"\"\"
        static_paths = {
            '/': 'index.html',
            '/index.html': 'index.html',
            '/style.css': 'style.css',
            '/app.js': 'app.js',
        }
        filename = static_paths.get(path, 'index.html')
        filepath = STATIC_DIR / filename
        if not filepath.exists():
            return None, None
        content_type = {
            '.html': 'text/html; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
            '.js': 'application/javascript; charset=utf-8',
        }.get(filepath.suffix, 'application/octet-stream')
        return filepath.read_bytes(), content_type


def serve_static(handler, path):
    \"\"\"Переопределение обработки статических файлов\"\"\"
    if path in ('/static', '/_static'):
        path = '/'
    data, ctype = StaticHandler.get_static_file(path)
    if data is None:
        handler.send_error(404)
        return
    handler.send_response(200)
    handler.send_header('Content-Type', ctype)
    handler.send_header('Content-Length', str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

"""
    with open(web_app_path, "a", encoding="utf-8") as f:
        f.write(static_code)
    print("Static serving added successfully")

