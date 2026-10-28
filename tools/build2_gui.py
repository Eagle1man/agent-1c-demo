# -*- coding: utf-8 -*-
"""Сборка SeedData.epf: новая обработка -> имя -> загрузка seed2 -> сохранить как.
Устойчивый вариант: ожидания с повторами, лог пишется всегда."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "build2_out.txt"
SRC_FILE = r"C:\1c_bases\epf_seed2\SeedData.xml"
EPF = r"C:\1c_bases\SeedData.epf"


def wait_for(fn, desc, lines, timeout=25):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            r = fn()
            if r is not None:
                return r
        except Exception:
            pass
        time.sleep(2)
    lines.append("!! timeout: " + desc)
    return None


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


def main():
    from pywinauto import Application
    lines = []
    p = subprocess.Popen([EXE, "DESIGNER", "/F", r"C:\1c_bases\DemoAgent"])
    try:
        time.sleep(30)
        app = Application(backend="uia").connect(process=p.pid)

        def get_main():
            wins = [w for w in app.windows() if w.window_text()]
            cfg = [w for w in wins if "Конфигуратор" in (w.window_text() or "")]
            if cfg:
                return cfg[0]
            return max(wins, key=lambda w: len(w.window_text())) if wins else None

        main = wait_for(get_main, "main window", lines, 40)
        if main is None:
            return
        main.set_focus()
        time.sleep(1)
        menu_ok = False
        for _ in range(4):
            main.type_keys("%{Ф}")
            time.sleep(3)
            try:
                items = [c.window_text() for c in main.descendants(control_type="MenuItem")]
                if any("Новый" in (t or "") for t in items):
                    menu_ok = True
                    break
            except Exception:
                pass
            time.sleep(2)
        lines.append("menu-open: " + str(menu_ok))
        if not menu_ok:
            snap(app, "no-menu", lines)
            return
        main.type_keys("Н")
        time.sleep(2)

        def get_newdlg():
            try:
                d = app.window(title="Выбор вида документа")
                d.wait("visible", timeout=2)
                return d
            except Exception:
                return None

        dlg = wait_for(get_newdlg, "new dialog", lines, 25)
        if dlg is None:
            return
        try:
            dlg.child_window(title="Внешняя обработка", control_type="ListItem").click_input()
            time.sleep(1)
            dlg.child_window(title="ОК", control_type="Button").click_input()
            time.sleep(5)
            lines.append("epf created")
        except Exception as exc:
            lines.append("!! create: " + str(exc)[:150])
            return
        # имя с выделением всего
        try:
            edits = main.descendants(control_type="Edit")
            edits[0].click_input()
            time.sleep(1)
            edits[0].type_keys("^aSeedData", with_spaces=True)
            time.sleep(1)
            lines.append("name set")
        except Exception as exc:
            lines.append("!! name: " + str(exc)[:150])
        # загрузка
        try:
            acts = [c for c in main.descendants(control_type="Button") if c.window_text() == "Действия"]
            acts[0].click_input()
            time.sleep(2)
            mi = [c for c in main.descendants(control_type="MenuItem")
                  if "Загрузить из файлов" in (c.window_text() or "")]
            mi[0].click_input()
            time.sleep(4)
            lines.append("load menu clicked")
        except Exception as exc:
            lines.append("!! loadmenu: " + str(exc)[:150])
            return

        def get_fd():
            for c in main.descendants(control_type="Window"):
                try:
                    if (c.window_text() or "").strip() == "Открытие":
                        return c
                except Exception:
                    continue
            return None

        fd = wait_for(get_fd, "open dialog", lines, 20)
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

        fn = wait_for(get_fn, "filename edit", lines, 15)
        if fn is None:
            return
        fn.set_focus()
        time.sleep(1)
        fn.type_keys(SRC_FILE, with_spaces=True)
        time.sleep(1)
        try:
            lines.append("typed-file=[" + str(fn.get_value()) + "]")
        except Exception:
            pass
        fn.type_keys("{ENTER}")
        time.sleep(10)
        lines.append("load file entered")
        # подтверждение сброса несохранённого: Нет
        try:
            for _ in range(3):
                found = False
                for w in app.windows():
                    try:
                        kids = [c for c in w.descendants(control_type="Button")
                                if (c.window_text() or "") == "Нет"]
                        txts = " ".join([(c.window_text() or "")[:80] for c in w.descendants()
                                         if c.element_info.control_type in ("Text", "Pane")][:6])
                        if kids and "несохраненные изменения" in txts:
                            kids[0].click_input()
                            time.sleep(6)
                            lines.append("confirm-no clicked")
                            found = True
                            break
                    except Exception:
                        continue
                if found:
                    break
                time.sleep(3)
        except Exception as exc:
            lines.append("!! confirm: " + str(exc)[:150])
        snap(app, "after-load", lines)
        # сохранить: заново найти главное окно
        try:
            wins = [w for w in app.windows() if w.window_text()]
            for w in wins:
                lines.append("win: " + (w.window_text() or "")[:100])
            mains = [w for w in wins if "Конфигуратор" in (w.window_text() or "")]
            if mains:
                main = mains[0]
            main.set_focus()
            time.sleep(1)
            main.type_keys("%{Ф}")
            time.sleep(2)
            main.type_keys("С")
            time.sleep(2)
            main.type_keys("{ENTER}")
            time.sleep(6)
            lines.append("saveas sent")
        except Exception as exc:
            lines.append("!! saveas: " + str(exc)[:200])
        snap(app, "after-saveas", lines)
        # ввести путь .epf в диалог сохранения
        try:
            sd = None
            for _ in range(5):
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
            fn = None
            for c in sd.descendants(control_type="Edit"):
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
            lines.append("save-typed=[" + str(fn.get_value()) + "]")
            fn.type_keys("{ENTER}")
            time.sleep(8)
            lines.append("save confirmed")
        except Exception as exc:
            lines.append("!! savefile: " + str(exc)[:200])
        snap(app, "after-savefile", lines)
    finally:
        try:
            OUT.write_text("\n".join(lines), encoding="utf-8")
            print("wrote " + str(OUT) + " lines=" + str(len(lines)))
        except Exception:
            pass


if __name__ == "__main__":
    main()
