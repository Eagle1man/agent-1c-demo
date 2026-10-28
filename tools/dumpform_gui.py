# -*- coding: utf-8 -*-
"""GUI: новая обработка -> добавить форму -> выгрузить в файлы -> снять результат."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "dumpform_out.txt"


def snap(app, tag, lines, limit=150):
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


def find_btn(scope, title):
    for c in scope.descendants(control_type="Button"):
        try:
            if (c.window_text() or "").strip() == title:
                return c
        except Exception:
            continue
    return None


def main():
    from pywinauto import Application
    lines = []
    p = subprocess.Popen([EXE, "DESIGNER", "/F", r"C:\1c_bases\DemoAgent"])
    time.sleep(30)
    app = Application(backend="uia").connect(process=p.pid)
    wins = [w for w in app.windows() if w.window_text()]
    main = max(wins, key=lambda w: len(w.window_text()))
    main.set_focus()
    time.sleep(1)
    main.type_keys("%{Ф}")
    time.sleep(2)
    main.type_keys("Н")
    time.sleep(3)
    dlg = app.window(title="Выбор вида документа")
    dlg.child_window(title="Внешняя обработка", control_type="ListItem").click_input()
    time.sleep(1)
    dlg.child_window(title="ОК", control_type="Button").click_input()
    time.sleep(5)
    edits = main.descendants(control_type="Edit")
    edits[0].click_input()
    time.sleep(1)
    edits[0].type_keys("SeedData", with_spaces=True)
    time.sleep(1)
    # выбрать "Формы" в списке
    for c in main.descendants(control_type="ListItem"):
        try:
            if (c.window_text() or "").strip() == "Формы":
                c.click_input()
                time.sleep(1)
                lines.append("forms selected")
                break
        except Exception:
            continue
    b = find_btn(main, "Добавить")
    if b is not None:
        b.click_input()
        time.sleep(5)
        lines.append("add clicked")
    else:
        lines.append("!! no add btn")
    # мастер: назначить основной + Готово
    try:
        wiz = app.window(title="Конструктор формы обработки")
        try:
            cb = [c for c in wiz.descendants(control_type="CheckBox")
                  if "основной" in (c.window_text() or "")]
            if cb:
                # TogglePattern: проверить состояние
                try:
                    st = cb[0].get_toggle_state()
                    lines.append("main-checkbox-state=%s" % st)
                    if st == 0:
                        cb[0].click_input()
                        time.sleep(1)
                        lines.append("main-checkbox checked")
                except Exception as exc:
                    lines.append("!! toggle: " + str(exc)[:120])
        except Exception as exc:
            lines.append("!! checkbox: " + str(exc)[:120])
        ok = [c for c in wiz.descendants(control_type="Button") if (c.window_text() or "") == "Готово"]
        ok[0].click_input()
        time.sleep(5)
        lines.append("wizard done")
    except Exception as exc:
        lines.append("!! wizard: " + str(exc)[:200])
    snap(app, "after-add", lines)
    # выгрузить в файлы
    try:
        acts = [c for c in main.descendants(control_type="Button") if c.window_text() == "Действия"]
        acts[0].click_input()
        time.sleep(2)
        mi = [c for c in main.descendants(control_type="MenuItem") if "Выгрузить в файлы" in (c.window_text() or "")]
        mi[0].click_input()
        time.sleep(4)
        lines.append("dump clicked")
    except Exception as exc:
        lines.append("!! dump: " + str(exc)[:200])
    snap(app, "after-dump-click", lines)
    # ввести путь целиком и Enter (для сохранения этого достаточно)
    try:
        sd = None
        for c in main.descendants(control_type="Window"):
            try:
                if (c.window_text() or "").strip() == "Сохранение":
                    sd = c
                    break
            except Exception:
                continue
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
        fn.type_keys("C:\\1c_bases\\epf_tpl", with_spaces=True)
        time.sleep(1)
        try:
            lines.append("save-typed=[" + str(fn.get_value()) + "]")
        except Exception as exc:
            lines.append("!! save-readback: " + str(exc)[:100])
        fn.type_keys("{ENTER}")
        time.sleep(5)
        lines.append("save enter sent")
        try:
            items = []
            for c in sd.descendants(control_type="ListItem"):
                try:
                    t = (c.window_text() or "").strip()
                    if t:
                        items.append(t)
                except Exception:
                    continue
            lines.append("save-list: " + str(items[:10]))
        except Exception as exc:
            lines.append("!! save-list: " + str(exc)[:100])
        try:
            btns = []
            for c in sd.descendants(control_type="Button"):
                try:
                    t = (c.window_text() or "").strip()
                    if t in ("Сохранить", "ОК", "OK", "Открыть", "Выбрать"):
                        btns.append((t, c))
                except Exception:
                    continue
            lines.append("save-btns: " + str([t for t, _ in btns]))
            for t, c in btns:
                if t == "Сохранить":
                    c.click_input()
                    time.sleep(10)
                    lines.append("save confirmed: Сохранить")
                    break
        except Exception as exc:
            lines.append("!! save-confirm: " + str(exc)[:150])
    except Exception as exc:
        lines.append("!! savepath: " + str(exc)[:200])
    snap(app, "after-save", lines)
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT) + " lines=" + str(len(lines)))


if __name__ == "__main__":
    main()
