# -*- coding: utf-8 -*-
"""Шаг 2: Файл->Новый... -> диалог, снять его дерево. Ничего не создаёт."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "explore2_out.txt"


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
    main = None
    for _ in range(12):
        try:
            wins = [w for w in app.windows() if w.window_text()]
            if wins:
                main = max(wins, key=lambda w: len(w.window_text()))
                break
        except Exception:
            pass
        time.sleep(5)
    if main is None:
        lines.append("!! no windows")
        OUT.write_text("\n".join(lines), encoding="utf-8")
        return
    lines.append("MAIN: " + main.window_text())
    main.set_focus()
    time.sleep(1)
    # Файл -> Новый... через клавиатуру
    main.type_keys("%{Ф}")
    time.sleep(2)
    main.type_keys("Н")
    time.sleep(3)
    snap(app, "new-dialog", lines)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT) + " lines=" + str(len(lines)))
    p.kill()


if __name__ == "__main__":
    main()
