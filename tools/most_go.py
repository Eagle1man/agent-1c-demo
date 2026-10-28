# -*- coding: utf-8 -*-
"""Запуск моста: security-Да, путь в поле, кнопка Запустить мост. Сеанс остаётся открытым."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
OUT = Path(__file__).resolve().parent / "most_go.txt"
EXCHANGE = r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\exchange"


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
                    lines.append("   [%s] %s" % (ct, t.strip()[:200]))
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
        p = subprocess.Popen([EXE, "ENTERPRISE", "/F", r"C:\1c_bases\DemoAgent",
                              "/Execute", r"C:\1c_bases\AgentMost.epf", "/DisableStartupDialogs"])
        Path(__file__).resolve().parent.joinpath("most_pid.txt").write_text(str(p.pid))
        time.sleep(30)
        app = Application(backend="uia").connect(process=p.pid)
        # security: первая кнопка Да
        for _ in range(4):
            for w in app.windows():
                try:
                    for c in w.descendants(control_type="Button"):
                        try:
                            if (c.window_text() or "").strip() == "Да":
                                c.click_input()
                                time.sleep(5)
                                lines.append("security-yes clicked")
                                break
                        except Exception:
                            continue
                except Exception:
                    continue
            time.sleep(2)
        time.sleep(8)
        snap(app, "form-state", lines)
        wins = [w for w in app.windows() if w.window_text()]
        main = max(wins, key=lambda w: len(w.window_text()))
        # поле: первое Edit, выделить всё, вписать путь
        try:
            edits = [c for c in main.descendants(control_type="Edit")]
            lines.append("edits: %d" % len(edits))
            if edits:
                edits[0].set_focus()
                time.sleep(1)
                edits[0].type_keys("^a", with_spaces=True)
                time.sleep(1)
                edits[0].type_keys(EXCHANGE, with_spaces=True)
                time.sleep(1)
                try:
                    lines.append("path-field=[" + str(edits[0].get_value()) + "]")
                except Exception as exc:
                    lines.append("!! readback: " + str(exc)[:100])
        except Exception as exc:
            lines.append("!! field: " + str(exc)[:150])
        # кнопка
        try:
            btns = [c for c in main.descendants(control_type="Button")
                    if (c.window_text() or "").strip() == "Запустить мост"]
            lines.append("start-btns: %d" % len(btns))
            if btns:
                btns[0].click_input()
                time.sleep(8)
                lines.append("start clicked")
        except Exception as exc:
            lines.append("!! start: " + str(exc)[:150])
        snap(app, "after-start", lines)
        lines.append("KEPT RUNNING pid=%d" % p.pid)
    finally:
        try:
            OUT.write_text("\n".join(lines), encoding="utf-8")
            print("wrote " + str(OUT) + " lines=" + str(len(lines)))
        except Exception:
            pass


if __name__ == "__main__":
    main()
