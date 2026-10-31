from pywinauto import Application
import sys

pid = int(sys.argv[1])
app = Application(backend="uia").connect(process=pid, timeout=20)
for w in app.windows():
    try:
        title = w.window_text()
    except Exception:
        continue
    print("=== WINDOW:", title)
    try:
        for c in w.descendants():
            try:
                t = c.window_text()
                ct = c.element_info.control_type
            except Exception:
                continue
            if t and t.strip():
                print(f"   [{ct}] {t.strip()[:200]}")
    except Exception as exc:
        print("   !! ", exc)
