# -*- coding: utf-8 -*-
"""Разведка GUI конфигуратора: открыть базу, Файл->Новый, снять деревья окон.
Ничего не сохраняет. Результат — explore_out.txt (UTF-8)."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "explore_out.txt"


def snap(app, tag, lines):
    lines.append("##### " + tag)
    try:
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
    except Exception as exc:
        lines.append("!! snap: " + str(exc))


def main():
    from pywinauto import Application
    lines = []
    p = subprocess.Popen([EXE, "DESIGNER", "/F", r"C:\1c_bases\DemoAgent"])
    time.sleep(20)
    app = Application(backend="uia").connect(process=p.pid)
    snap(app, "designer-main", lines)
    # Файл -> Новый
    try:
        main = app.window(title_re=".*Конфигуратор.*")
        main.set_focus()
        time.sleep(1)
        main.type_keys("%{Ф}")
        time.sleep(2)
        snap(app, "after-alt-f", lines)
    except Exception as exc:
        lines.append("!! menu: " + str(exc))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT) + " lines=" + str(len(lines)))
    p.kill()


if __name__ == "__main__":
    main()
