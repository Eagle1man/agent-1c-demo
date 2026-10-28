# -*- coding: utf-8 -*-
"""Шаг 4: открыть редактор внешней обработки, снять ВСЕ контролы с типами."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "explore4_out.txt"


def dump(app, lines):
    for w in app.windows():
        try:
            title = w.window_text()
        except Exception:
            continue
        lines.append("=== WINDOW: " + (title or "<no title>"))
        try:
            for c in w.descendants():
                try:
                    info = c.element_info
                    t = c.window_text() or ""
                    lines.append("   [%s] '%s'" % (info.control_type, t[:120]))
                except Exception as exc:
                    lines.append("   !! " + str(exc)[:100])
        except Exception as exc:
            lines.append("   !! enum: " + str(exc))


def main():
    from pywinauto import Application
    lines = []
    p = subprocess.Popen([EXE, "DESIGNER", "/F", r"C:\1c_bases\DemoAgent"])
    time.sleep(30)
    app = Application(backend="uia").connect(process=p.pid)
    wins = [w for w in app.windows() if w.window_text()]
    main = max(wins, key=lambda w: len(w.window_text()))
    main.set_focus()
    time.sleep(1)
    main.type_keys("%{Ф}")
    time.sleep(2)
    main.type_keys("Н")
    time.sleep(3)
    dlg = app.window(title="Выбор вида документа")
    dlg.child_window(title="Внешняя обработка", control_type="ListItem").click_input()
    time.sleep(1)
    dlg.child_window(title="ОК", control_type="Button").click_input()
    time.sleep(6)
    dump(app, lines)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT) + " lines=" + str(len(lines)))


if __name__ == "__main__":
    main()
