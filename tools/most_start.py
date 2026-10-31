# -*- coding: utf-8 -*-
"""Запуск моста: открыть форму, вписать путь exchange, нажать Запустить мост.
Сеанс 1С ОСТАЁТСЯ открытым (PID в most_pid.txt)."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "most_start.txt"
EXCHANGE = r"D:\agent-1c-demo\exchange"


def snap(app, tag, lines, limit=80):
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
                    lines.append("   [%s] %s" % (ct, t.strip()[:200]))
                    n += 1
                    if n > limit:
                        lines.append("   ... truncated")
                        return
        except Exception as exc:
            lines.append("   !! enum: " + str(exc))


def find_btn(scope, title):
    found = []
    for c in scope.descendants(control_type="Button"):
        try:
            if (c.window_text() or "").strip() == title:
                found.append(c)
        except Exception:
            continue
    return found


def main():
    from pywinauto import Application
    lines = []
    try:
        p = subprocess.Popen([EXE, "ENTERPRISE", "/F", r"C:\1c_bases\DemoAgent",
                              "/Execute", r"C:\1c_bases\AgentMost.epf", "/DisableStartupDialogs"])
        Path(__file__).resolve().parent.joinpath("most_pid.txt").write_text(str(p.pid))
        time.sleep(35)
        app = Application(backend="uia").connect(process=p.pid)
        # диалог безопасности: ответить Да
        try:
            for _ in range(4):
                done = False
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
                            done = True
                            break
                    except Exception:
                        continue
                if done:
                    break
                time.sleep(3)
        except Exception as exc:
            lines.append("!! security: " + str(exc)[:150])
        snap(app, "form-state", lines)
        wins = [w for w in app.windows() if w.window_text()]
        main = max(wins, key=lambda w: len(w.window_text()))
        # поле пути: найти Edit, вписать exchange
        fld = None
        for c in main.descendants(control_type="Edit"):
            try:
                fld = c
                break
            except Exception:
                continue
        if fld is not None:
            fld.set_focus()
            time.sleep(1)
            fld.type_keys("^a", with_spaces=True)
            time.sleep(1)
            fld.type_keys(EXCHANGE, with_spaces=True)
            time.sleep(1)
            try:
                lines.append("path-field=[" + str(fld.get_value()) + "]")
            except Exception as exc:
                lines.append("!! readback: " + str(exc)[:100])
        else:
            lines.append("!! no edit field")
        # кнопка
        btns = find_btn(main, "Запустить мост")
        lines.append("start-btns: %d" % len(btns))
        if btns:
            btns[0].click_input()
            time.sleep(8)
            lines.append("start clicked")
        snap(app, "after-start", lines)
        lines.append("1C KEPT RUNNING pid=%d" % p.pid)
    finally:
        try:
            OUT.write_text("\n".join(lines), encoding="utf-8")
            print("wrote " + str(OUT) + " lines=" + str(len(lines)))
        except Exception:
            pass


if __name__ == "__main__":
    main()
