# -*- coding: utf-8 -*-
"""Сборка SeedData.epf: новая обработка -> имя -> загрузка из файлов -> сохранить как.
Логика ветвления по факту: स्नैपшоты после каждого шага в build_seed_out.txt."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "build_seed_out.txt"
SRC = r"C:\1c_bases\epf_seed"
EPF = r"C:\1c_bases\SeedData.epf"


def snap(app, tag, lines, limit=120):
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


def set_clip_file(path):
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Content -Raw -LiteralPath '" + path + "' | Set-Clipboard"],
                   check=True)


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
    # имя
    edits = main.descendants(control_type="Edit")
    edits[0].click_input()
    time.sleep(1)
    edits[0].type_keys("SeedData", with_spaces=True)
    time.sleep(1)
    lines.append("name set")
    # действия -> загрузить из файлов
    acts = [c for c in main.descendants(control_type="Button") if c.window_text() == "Действия"]
    acts[0].click_input()
    time.sleep(2)
    mi = [c for c in main.descendants(control_type="MenuItem") if "Загрузить из файлов" in (c.window_text() or "")]
    mi[0].click_input()
    time.sleep(4)
    # диалог выбора каталога: дочернее окно "Открытие" перебором потомков
    fd = None
    for _ in range(6):
        try:
            for c in main.descendants(control_type="Window"):
                try:
                    if (c.window_text() or "").strip() == "Открытие":
                        fd = c
                        break
                except Exception:
                    continue
            if fd is not None:
                break
        except Exception:
            pass
        time.sleep(3)
    if fd is None:
        lines.append("!! no open-dialog")
        snap(app, "no-dialog", lines)
        OUT.write_text("\n".join(lines), encoding="utf-8")
        print("wrote " + str(OUT))
        return
    def find_in(parent, title, ctype):
        for c in parent.descendants(control_type=ctype):
            try:
                if (c.window_text() or "").strip() == title:
                    return c
            except Exception:
                continue
        return None

    def focus_edit(edit, tag):
        for _ in range(4):
            try:
                try:
                    edit.set_focus()
                except Exception:
                    edit.click_input()
                time.sleep(1)
                try:
                    if edit.has_keyboard_focus():
                        lines.append(tag + ": focused")
                        return True
                except Exception:
                    lines.append(tag + ": focus-unknown, trying type anyway")
                    return True
            except Exception as exc:
                lines.append(tag + " focus err: " + str(exc)[:100])
            time.sleep(1)
        lines.append(tag + ": NOT focused")
        return False

    def tree_names():
        names = []
        try:
            for c in fd.descendants(control_type="TreeItem"):
                try:
                    t = (c.window_text() or "").strip()
                    if t:
                        names.append(t)
                except Exception:
                    continue
        except Exception:
            pass
        return names

    def click_tree(name):
        for _ in range(3):
            try:
                for c in fd.descendants(control_type="TreeItem"):
                    try:
                        if (c.window_text() or "").strip() == name:
                            c.click_input()
                            time.sleep(2)
                            return True
                    except Exception:
                        continue
            except Exception:
                pass
            time.sleep(2)
        lines.append("!! no treeitem: " + name)
        return False

    fn = find_in(fd, "Имя файла:", "Edit")
    if fn is not None and focus_edit(fn, "fileedit"):
        fn.type_keys("C:\\1c_bases", with_spaces=True)
        time.sleep(1)
        try:
            lines.append("typed=[" + str(fn.get_value()) + "]")
        except Exception as exc:
            lines.append("!! get_value: " + str(exc)[:100])
        fn.type_keys("{ENTER}")
        time.sleep(5)
        lines.append("enter sent")
        try:
            items = []
            for c in fd.descendants(control_type="ListItem"):
                try:
                    t = (c.window_text() or "").strip()
                    if t:
                        items.append(t)
                except Exception:
                    continue
            lines.append("list-has-seed: " + str("epf_seed" in items))
            for c in fd.descendants(control_type="ListItem"):
                try:
                    if (c.window_text() or "").strip() == "epf_seed":
                        c.click_input()
                        time.sleep(2)
                        lines.append("sel: epf_seed")
                        break
                except Exception:
                    continue
        except Exception as exc:
            lines.append("!! list: " + str(exc)[:100])
    else:
        lines.append("!! no fileedit")
    # кнопка Открыть: хоткей Alt+O, затем клик как запасной
    # ВАРИАНТ C: полный путь к корневому файлу прямо в поле имени
    try:
        fn3 = find_in(fd, "Имя файла:", "Edit")
        if fn3 is not None and focus_edit(fn3, "fileedit3"):
            fn3.type_keys("C:\\1c_bases\\epf_seed\\ExternalDataProcessor.xml", with_spaces=True)
            time.sleep(1)
            try:
                lines.append("typed-file=[" + str(fn3.get_value()) + "]")
            except Exception as exc:
                lines.append("!! get_value4: " + str(exc)[:100])
            fn3.type_keys("{ENTER}")
            time.sleep(10)
            lines.append("file-enter sent")
    except Exception as exc:
        lines.append("!! variantC: " + str(exc))
        time.sleep(10)
        lines.append("open clicked")
    except Exception as exc:
        lines.append("!! open: " + str(exc))
    snap(app, "after-open", lines)
    # кнопка Подробно в окне ошибки
    try:
        dets = [c for c in main.descendants(control_type="Button")
                if (c.window_text() or "").strip() == "Подробно..."]
        if dets:
            dets[0].click_input()
            time.sleep(3)
            lines.append("details clicked")
            snap(app, "after-details", lines)
        else:
            lines.append("no details btn")
    except Exception as exc:
        lines.append("!! details: " + str(exc))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT) + " lines=" + str(len(lines)))


if __name__ == "__main__":
    main()
