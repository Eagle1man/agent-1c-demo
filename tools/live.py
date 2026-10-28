# -*- coding: utf-8 -*-
"""Снапшот живой сессии по PID из файла."""
import time
from pathlib import Path

d = Path(__file__).resolve().parent


def main():
    from pywinauto import Application
    lines = []
    pid = None
    cands = sorted(d.glob("*_pid.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    for f in cands:
        try:
            pid = int(f.read_text().strip().split()[0])
            lines.append("trying pid=%d from %s" % (pid, f.name))
            break
        except Exception:
            continue
    if pid is None:
        lines.append("no pid file")
        (d / "live.txt").write_text("\n".join(lines), encoding="utf-8")
        return
    app = Application(backend="uia").connect(process=pid)
    time.sleep(2)
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
    (d / "live.txt").write_text("\n".join(lines), encoding="utf-8")
    print("wrote live.txt lines=" + str(len(lines)))


if __name__ == "__main__":
    main()
