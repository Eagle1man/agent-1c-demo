# -*- coding: utf-8 -*-
"""Открыть мост, в диалоге ошибки нажать 'Сформировать отчет', снять текст."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "most_err.txt"


def main():
    from pywinauto import Application
    lines = []
    try:
        p = subprocess.Popen([EXE, "ENTERPRISE", "/F", r"C:\1c_bases\DemoAgent",
                              "/Execute", r"C:\1c_bases\AgentMost.epf", "/DisableStartupDialogs"])
        time.sleep(35)
        app = Application(backend="uia").connect(process=p.pid)
        # ответить Да на безопасность если есть
        for _ in range(3):
            for w in app.windows():
                try:
                    kids = [c for c in w.descendants(control_type="Button")
                            if (c.window_text() or "") == "Да"]
                    txts = " ".join([(c.window_text() or "")[:60] for c in w.descendants()
                                     if c.element_info.control_type in ("Text", "Pane")][:4])
                    if kids and "безопасности" in txts:
                        kids[0].click_input()
                        time.sleep(5)
                        lines.append("security-yes clicked")
                        break
                except Exception:
                    continue
            time.sleep(2)
        # искать ссылку отчета
        for _ in range(3):
            for w in app.windows():
                try:
                    for c in w.descendants():
                        try:
                            t = (c.window_text() or "")
                            ct = c.element_info.control_type
                        except Exception:
                            continue
                        if "отчет об ошибке" in t.lower() and ct in ("Hyperlink", "Button", "Text"):
                            lines.append("found report link [%s]: %s" % (ct, t[:80]))
                            try:
                                c.click_input()
                                time.sleep(4)
                                lines.append("report clicked")
                            except Exception as exc:
                                lines.append("!! click: " + str(exc)[:120])
                            raise StopIteration
                except StopIteration:
                    break
                except Exception:
                    continue
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
                        lines.append("   [%s] %s" % (ct, t.strip()[:250]))
            except Exception as exc:
                lines.append("   !! enum: " + str(exc))
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print("wrote " + str(OUT) + " lines=" + str(len(lines)))
    except Exception as exc:
        OUT.write_text("FATAL: " + str(exc)[:300], encoding="utf-8")
        print("fatal")


if __name__ == "__main__":
    main()
