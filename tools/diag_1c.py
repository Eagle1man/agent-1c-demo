# -*- coding: utf-8 -*-
"""Диагностика живого окна 1С: полное дерево контролов + скриншот окна 1С."""
from pathlib import Path

OUT = Path(r"D:\agent-1c-demo\diag_1c_out.txt")
log = []


def main():
    from pywinauto import Application
    app = Application(backend="uia").connect(process=11292)
    for w in app.windows():
        try:
            title = w.window_text() or ""
            cls = ""
            try:
                cls = w.element_info.class_name or ""
            except Exception:
                pass
            log.append("=== WINDOW %r class=%s" % (title, cls))
            n = 0
            for c in w.descendants():
                try:
                    t = (c.window_text() or "").strip()
                    ct = c.element_info.control_type
                except Exception:
                    continue
                if t:
                    log.append("   [%s] %r" % (ct, t[:150]))
                    n += 1
                if n > 160:
                    log.append("   ... обрезано")
                    break
        except Exception as exc:
            log.append("!! " + str(exc)[:90])
    # скриншот именно окна 1С
    for w in app.windows():
        try:
            t = w.window_text() or ""
            if "ДемоАгент" in t or "Предприятие" in t:
                w.capture_as_image().save(r"D:\agent-1c-demo\diag_1c_screen.png")
                log.append("скриншот окна %r сохранён" % t[:40])
                break
        except Exception as exc:
            log.append("!! shot " + str(exc)[:60])


try:
    main()
finally:
    OUT.write_text("\n".join(log), encoding="utf-8")
    print("строк:", len(log))
