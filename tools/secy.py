# -*- coding: utf-8 -*-
"""Ответить Да на диалог безопасности в живой сессии (PID из файла)."""
import time
from pathlib import Path

d = Path(__file__).resolve().parent


def main():
    from pywinauto import Application
    lines = []
    pid = int((d / "testfull2_pid.txt").read_text().strip())
    lines.append("pid=%d" % pid)
    app = Application(backend="uia").connect(process=pid)
    for w in app.windows():
        try:
            title = w.window_text()
        except Exception:
            continue
        lines.append("TOP: " + (title or "<no>"))
        try:
            for c in w.descendants(control_type="Button"):
                try:
                    t = (c.window_text() or "").strip()
                    if t in ("Да", "Нет", "ОК", "OK", "Отмена"):
                        lines.append("  BTN: " + t)
                        if t == "Да":
                            # проверить рядом текст безопасности
                            c.click_input()
                            time.sleep(4)
                            lines.append("  CLICKED Да")
                except Exception as exc:
                    lines.append("  !! btn: " + str(exc)[:100])
        except Exception as exc:
            lines.append("  !! enum: " + str(exc)[:100])
    time.sleep(6)
    for w in app.windows():
        try:
            lines.append("AFTER TOP: " + (w.window_text() or "<no>")[:100])
        except Exception:
            continue
    (d / "secy.txt").write_text("\n".join(lines), encoding="utf-8")
    print("wrote secy.txt")


if __name__ == "__main__":
    main()
