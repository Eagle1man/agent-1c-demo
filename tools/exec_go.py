# -*- coding: utf-8 -*-
"""Запуск EPF: ответить Да на безопасность, снять форму. Сеанс остаётся открытым."""
import subprocess
import sys
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"


def main():
    from pywinauto import Application
    epf = sys.argv[1]
    tag = sys.argv[2] if len(sys.argv) > 2 else "exec"
    out = Path(__file__).resolve().parent / (tag + "_run.txt")
    lines = []
    try:
        p = subprocess.Popen([EXE, "ENTERPRISE", "/F", r"C:\1c_bases\DemoAgent",
                              "/Execute", epf, "/DisableStartupDialogs"])
        Path(__file__).resolve().parent.joinpath(tag + "_pid.txt").write_text(str(p.pid))
        time.sleep(30)
        app = Application(backend="uia").connect(process=p.pid)
        for _ in range(4):
            for w in app.windows():
                try:
                    for c in w.descendants(control_type="Button"):
                        try:
                            if (c.window_text() or "").strip() == "Да":
                                c.click_input()
                                time.sleep(5)
                                lines.append("security-yes clicked")
                                break
                        except Exception:
                            continue
                except Exception:
                    continue
            time.sleep(2)
        time.sleep(10)
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
        lines.append("KEPT RUNNING pid=%d" % p.pid)
        out.write_text("\n".join(lines), encoding="utf-8")
        print("wrote " + str(out) + " lines=" + str(len(lines)))
    except Exception as exc:
        out.write_text("FATAL: " + str(exc)[:300], encoding="utf-8")
        print("fatal")


if __name__ == "__main__":
    main()
