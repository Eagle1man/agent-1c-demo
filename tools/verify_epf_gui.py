# -*- coding: utf-8 -*-
"""Проверка SeedData.epf: открыть через тулбар, выгрузить в файлы."""
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from guihelp import ensure_ru, wait_for  # noqa: E402

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "verify_epf_out.txt"
EPF = r"C:\1c_bases\SeedData.epf"
DUMP = r"C:\1c_bases\epf_check"


Path(DUMP).mkdir(parents=True, exist_ok=True)


def snap(app, tag, lines, limit=60):
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


def click_btn(scope, title, lines, tag):
    for c in scope.descendants(control_type="Button"):
        try:
            if (c.window_text() or "").strip() == title:
                c.click_input()
                time.sleep(2)
                lines.append(tag + ": " + title)
                return c
        except Exception:
            continue
    lines.append("!! no btn: " + title)
    return None


def main():
    from pywinauto import Application
    lines = []
    try:
        p = subprocess.Popen([EXE, "DESIGNER", "/F", r"C:\1c_bases\DemoAgent"])
        time.sleep(30)
        app = Application(backend="uia").connect(process=p.pid)

        def get_main():
            wins = [w for w in app.windows() if w.window_text()]
            cfg = [w for w in wins if "Конфигуратор" in (w.window_text() or "")]
            return cfg[0] if cfg else None

        main = wait_for(get_main, "main window", lines, 40)
        if main is None:
            return
        main.set_focus()
        time.sleep(1)
        ensure_ru(main.handle)
        if click_btn(main, "Открыть...", lines, "toolbar") is None:
            return
        time.sleep(8)
        for w in app.windows():
            try:
                lines.append("topwin: " + (w.window_text() or "")[:80])
            except Exception:
                pass
        time.sleep(5)

        def get_fd():
            for c in main.descendants(control_type="Window"):
                try:
                    if (c.window_text() or "").strip() == "Открытие":
                        return c
                except Exception:
                    continue
            return None

        fd = wait_for(get_fd, "open dialog", lines, 15)
        if fd is None:
            return

        def get_fn():
            for c in fd.descendants(control_type="Edit"):
                try:
                    if (c.window_text() or "").strip() == "Имя файла:":
                        return c
                except Exception:
                    continue
            return None

        fn = wait_for(get_fn, "filename edit", lines, 10)
        if fn is None:
            return
        fn.set_focus()
        time.sleep(1)
        fn.type_keys(EPF, with_spaces=True)
        time.sleep(1)
        fn.type_keys("{ENTER}")
        time.sleep(8)
        lines.append("epf open entered")
        snap(app, "after-open-epf", lines)
        # Действия -> Выгрузить в файлы -> путь
        try:
            mi = []
            for _ in range(5):
                try:
                    acts = [c for c in main.descendants(control_type="Button") if c.window_text() == "Действия"]
                    if acts:
                        acts[0].click_input()
                        time.sleep(4)
                    for w in app.windows():
                        try:
                            for c in w.descendants(control_type="MenuItem"):
                                try:
                                    if "Выгрузить в файлы" in (c.window_text() or ""):
                                        mi.append(c)
                                except Exception:
                                    continue
                        except Exception:
                            continue
                    if mi:
                        break
                except Exception:
                    pass
                time.sleep(2)
            mi[0].click_input()
            time.sleep(4)
            lines.append("dump menu clicked")
        except Exception as exc:
            lines.append("!! dumpmenu: " + str(exc)[:150])
            return
        # диалог Сохранение: ввести путь
        try:
            sd = None
            for _ in range(6):
                for c in main.descendants(control_type="Window"):
                    try:
                        if (c.window_text() or "").strip() == "Сохранение":
                            sd = c
                            break
                    except Exception:
                        continue
                if sd is not None:
                    break
                time.sleep(2)
            fn2 = None
            for c in sd.descendants(control_type="Edit"):
                try:
                    if (c.window_text() or "").strip() == "Имя файла:":
                        fn2 = c
                        break
                except Exception:
                    continue
            fn2.set_focus()
            time.sleep(1)
            fn2.type_keys(DUMP, with_spaces=True)
            time.sleep(1)
            lines.append("dump-typed=[" + str(fn2.get_value()) + "]")
            fn2.type_keys("{ENTER}")
            time.sleep(8)
            lines.append("dump path entered")
        except Exception as exc:
            lines.append("!! dumppath: " + str(exc)[:200])
        snap(app, "after-dump-path", lines)
    finally:
        try:
            OUT.write_text("\n".join(lines), encoding="utf-8")
            print("wrote " + str(OUT) + " lines=" + str(len(lines)))
        except Exception:
            pass


if __name__ == "__main__":
    main()
