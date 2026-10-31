# -*- coding: utf-8 -*-
"""Открыть AgentMost.epf через /Execute, снять форму, вписать путь exchange."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "most_open.txt"
EXCHANGE = r"D:\agent-1c-demo\dist\exchange"


def main():
    from pywinauto import Application
    lines = []
    try:
        p = subprocess.Popen([EXE, "ENTERPRISE", "/F", r"C:\1c_bases\DemoAgent",
                              "/Execute", r"C:\1c_bases\AgentMost.epf"])
        time.sleep(35)
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
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print("wrote " + str(OUT) + " lines=" + str(len(lines)))
    except Exception as exc:
        OUT.write_text("FATAL: " + str(exc)[:300], encoding="utf-8")
        print("fatal")


if __name__ == "__main__":
    main()
