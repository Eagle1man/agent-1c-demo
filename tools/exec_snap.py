# -*- coding: utf-8 -*-
"""Снапшот окон ENTERPRISE /Execute: полный дамп потомков главного окна."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "exec_snap.txt"


def main():
    from pywinauto import Application
    lines = []
    p = subprocess.Popen([EXE, "ENTERPRISE", "/F", r"C:\1c_bases\DemoAgent",
                          "/Execute", r"C:\1c_bases\SeedData.epf", "/DisableStartupDialogs"])
    time.sleep(35)
    try:
        app = Application(backend="uia").connect(process=p.pid)
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
                        lines.append("   [%s] %s" % (ct, t.strip()[:200]))
            except Exception as exc:
                lines.append("   !! enum: " + str(exc))
    except Exception as exc:
        lines.append("!! connect: " + str(exc)[:200])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT) + " lines=" + str(len(lines)))


if __name__ == "__main__":
    main()
