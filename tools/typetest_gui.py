# -*- coding: utf-8 -*-
"""Тест ввода: открыть диалог, ввести маркер в Имя файла, прочитать get_value."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "typetest_out.txt"


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
    acts = [c for c in main.descendants(control_type="Button") if c.window_text() == "Действия"]
    acts[0].click_input()
    time.sleep(2)
    mi = [c for c in main.descendants(control_type="MenuItem") if "Загрузить из файлов" in (c.window_text() or "")]
    mi[0].click_input()
    time.sleep(4)
    fd = None
    for _ in range(5):
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
    lines.append("fd=" + str(fd is not None))
    fn = None
    for c in fd.descendants(control_type="Edit"):
        try:
            if (c.window_text() or "").strip() == "Имя файла:":
                fn = c
                break
        except Exception:
            continue
    lines.append("fn=" + str(fn is not None))
    # 1. прямое чтение текущего значения
    try:
        lines.append("before=[" + str(fn.get_value()) + "]")
    except Exception as exc:
        lines.append("!! get_value: " + str(exc)[:150])
    fn.set_focus()
    time.sleep(1)
    # 2. ввод латиницы БЕЗ буфера
    fn.type_keys("C:\\zzmarker", with_spaces=True)
    time.sleep(1)
    try:
        lines.append("after-type=[" + str(fn.get_value()) + "]")
    except Exception as exc:
        lines.append("!! get_value2: " + str(exc)[:150])
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print("wrote " + str(OUT))


if __name__ == "__main__":
    main()
