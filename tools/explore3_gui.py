# -*- coding: utf-8 -*-
"""Шаг 3: Новый -> Внешняя обработка -> OK -> снять окно редактора. Не сохраняет."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "explore3_out.txt"


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
                except Exception:
                    continue
                if t and t.strip():
                    lines.append("   | " + t.strip()[:200])
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
    # диалог "Выбор вида документа": выбрать "Внешняя обработка"
    try:
        dlg = app.window(title="Выбор вида документа")
        dlg.set_focus()
        time.sleep(1)
        item = dlg.child_window(title="Внешняя обработка", control_type="ListItem")
        item.click_input()
        time.sleep(1)
        lines.append("SELECTED внешняя обработка")
    except Exception as exc:
        lines.append("!! select: " + str(exc))
        # запасной вариант: клавиатура
        try:
            dlg = app.window(title="Выбор вида документа")
            dlg.set_focus()
            dlg.type_keys("В")
            time.sleep(1)
            lines.append("keyboard jump done")
        except Exception as exc2:
            lines.append("!! kbd: " + str(exc2))
    snap(app, "dialog-after-select", lines)
    # OK
    try:
        dlg = app.window(title="Выбор вида документа")
        ok = dlg.child_window(title="ОК", control_type="Button")
        ok.click_input()
        time.sleep(5)
        lines.append("OK clicked")
    except Exception as exc:
        lines.append("!! ok: " + str(exc))
    snap(app, "after-ok", lines)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT) + " lines=" + str(len(lines)))


if __name__ == "__main__":
    main()
