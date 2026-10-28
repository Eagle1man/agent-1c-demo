# -*- coding: utf-8 -*-
"""Разведка редактора формы: открыть форму SeedData.epf, снять вкладки/панели."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "formedt_out.txt"
EPF = r"C:\1c_bases\SeedData.epf"


def snap(app, tag, lines, limit=100):
    lines.append("##### " + tag)
    n = 0
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
                    lines.append("   [%s] %s" % (ct, t.strip()[:160]))
                    n += 1
                    if n > limit:
                        lines.append("   ... truncated")
                        return
        except Exception as exc:
            lines.append("   !! enum: " + str(exc))


def main():
    from pywinauto import Application
    lines = []
    try:
        p = subprocess.Popen([EXE, "DESIGNER", "/F", r"C:\1c_bases\DemoAgent"])
        time.sleep(30)
        app = Application(backend="uia").connect(process=p.pid)
        wins = [w for w in app.windows() if w.window_text()]
        cfg = [w for w in wins if "Конфигуратор" in (w.window_text() or "")]
        main = cfg[0] if cfg else max(wins, key=lambda w: len(w.window_text()))
        main.set_focus()
        time.sleep(1)
        # Файл -> Открыть -> epf
        for _ in range(4):
            main.type_keys("%{Ф}")
            time.sleep(3)
            try:
                items = [c.window_text() for c in main.descendants(control_type="MenuItem")]
                if any("Открыть" in (t or "") and "конфигурац" not in (t or "").lower() for t in items):
                    break
            except Exception:
                pass
            time.sleep(2)
        main.type_keys("О")
        time.sleep(3)
        fd = None
        for _ in range(8):
            for c in main.descendants(control_type="Window"):
                try:
                    if (c.window_text() or "").strip() == "Открытие":
                        fd = c
                        break
                except Exception:
                    continue
            if fd is not None:
                break
            time.sleep(2)
        fn = None
        for c in fd.descendants(control_type="Edit"):
            try:
                if (c.window_text() or "").strip() == "Имя файла:":
                    fn = c
                    break
            except Exception:
                continue
        fn.set_focus()
        time.sleep(1)
        fn.type_keys(EPF, with_spaces=True)
        time.sleep(1)
        fn.type_keys("{ENTER}")
        time.sleep(8)
        lines.append("epf opened")
        # открыть форму: выбрать Формы, двойной клик по форме
        try:
            for c in main.descendants(control_type="ListItem"):
                try:
                    if (c.window_text() or "").strip() == "Формы":
                        c.click_input()
                        time.sleep(2)
                        lines.append("forms section selected")
                        break
                except Exception:
                    continue
            for c in main.descendants(control_type="ListItem"):
                try:
                    if (c.window_text() or "").strip() == "Форма":
                        c.double_click_input()
                        time.sleep(5)
                        lines.append("form dblclicked")
                        break
                except Exception:
                    continue
        except Exception as exc:
            lines.append("!! formopen: " + str(exc)[:150])
        snap(app, "epf-editor", lines)
    finally:
        try:
            OUT.write_text("\n".join(lines), encoding="utf-8")
            print("wrote " + str(OUT) + " lines=" + str(len(lines)))
        except Exception:
            pass


if __name__ == "__main__":
    main()
