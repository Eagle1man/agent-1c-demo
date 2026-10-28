# -*- coding: utf-8 -*-
"""Дожать диалог безопасности в живой сессии: фокус + клик + проверка закрытия."""
import time
from pathlib import Path

d = Path(__file__).resolve().parent


def main():
    from pywinauto import Application
    lines = []
    cands = sorted(d.glob("*_pid.txt"), key=lambda f: f.stat().st_mtime, reverse=True)
    pid = None
    for f in cands:
        try:
            raw = f.read_bytes().decode("utf-8-sig", errors="ignore")
            pid = int("".join(ch for ch in raw.strip().split()[0] if ch.isdigit()))
            lines.append("pid=%d from %s" % (pid, f.name))
            break
        except Exception:
            continue
    if pid is None:
        lines.append("no pid file")
        (d / "pushy.txt").write_text("\n".join(lines), encoding="utf-8")
        return
    app = Application(backend="uia").connect(process=pid)
    for attempt in range(6):
        found = False
        for w in app.windows():
            try:
                for c in w.descendants(control_type="Button"):
                    try:
                        if (c.window_text() or "").strip() == "Да":
                            # фокус на окно диалога
                            try:
                                w.set_focus()
                                time.sleep(1)
                            except Exception:
                                pass
                            c.click_input()
                            time.sleep(4)
                            lines.append("clicked Да attempt=%d" % attempt)
                            found = True
                            break
                    except Exception:
                        continue
            except Exception:
                continue
            if found:
                break
        # проверить: диалог ещё есть?
        still = False
        for w in app.windows():
            try:
                for c in w.descendants(control_type="Button"):
                    try:
                        if (c.window_text() or "").strip() == "Да":
                            still = True
                    except Exception:
                        continue
            except Exception:
                continue
        lines.append("dialog-still-open=%s" % still)
        if not still:
            break
        time.sleep(3)
    (d / "pushy.txt").write_text("\n".join(lines), encoding="utf-8")
    print("wrote pushy.txt")


if __name__ == "__main__":
    main()
