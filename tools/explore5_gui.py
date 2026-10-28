# -*- coding: utf-8 -*-
"""Шаг 5: открыть Действия в редакторе обработки, снять меню."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "explore5_out.txt"


def snap(app, tag, lines):
    lines.append("##### " + tag)
    for w in app.windows():
        try:
            title = w.window_text()
        except Exception:
            continue
        lines.append("=== WINDOW: " + (title or "<no title>"))
        try:
            for c in w.descendants():
                try:
                    t = c.window_text()
                    ct = c.element_info.control_type
                except Exception:
                    continue
                if t and t.strip():
                    lines.append("   [%s] %s" % (ct, t.strip()[:160]))
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
    # Имя
    edits = main.descendants(control_type="Edit")
    lines.append("edits found: %d" % len(edits))
    try:
        edits[0].click_input()
        time.sleep(1)
        edits[0].type_keys("SeedData", with_spaces=True)
        time.sleep(1)
        lines.append("name typed")
    except Exception as exc:
        lines.append("!! name: " + str(exc))
    # Действия
    try:
        acts = [c for c in main.descendants(control_type="Button") if c.window_text() == "Действия"]
        lines.append("actions btns: %d" % len(acts))
        acts[0].click_input()
        time.sleep(2)
        lines.append("actions clicked")
    except Exception as exc:
        lines.append("!! actions: " + str(exc))
    snap(app, "actions-menu", lines)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT) + " lines=" + str(len(lines)))


if __name__ == "__main__":
    main()
