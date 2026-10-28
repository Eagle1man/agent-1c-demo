# -*- coding: utf-8 -*-
"""Живой тест: окно диалога в 1С — печатаем фразу и читаем историю."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
BASE = r"C:\1c_bases\DemoAgentT"
EPF = r"C:\1c_bases\AgentMost.epf"
OUT = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\chat_1c_out.txt")
PHRASE = "покажи задолженность контрагентов"
log = []


def snap(app, tag, limit=120):
    log.append("##### " + tag)
    n = 0
    for w in app.windows():
        try:
            title = w.window_text()
        except Exception:
            continue
        log.append("=== WINDOW: " + (title or "<no title>"))
        for c in w.descendants():
            try:
                t = c.window_text()
                ct = c.element_info.control_type
            except Exception:
                continue
            if t and t.strip():
                log.append("   [%s] %s" % (ct, t.strip()[:160]))
                n += 1
                if n > limit:
                    log.append("   ... truncated")
                    return


def edits(scope):
    res = []
    for c in scope.descendants(control_type="Edit"):
        try:
            val = c.get_value()
            rect = c.rectangle()
        except Exception:
            continue
        res.append((c, val, rect))
    return sorted(res, key=lambda x: (x[2].top, x[2].left))


def main():
    from pywinauto import Application
    p = subprocess.Popen([EXE, "ENTERPRISE", "/F", BASE, "/Execute", EPF,
                          "/DisableStartupDialogs"])
    log.append("1C pid=%d" % p.pid)
    time.sleep(45)
    app = Application(backend="uia").connect(process=p.pid)
    for _ in range(5):
        done = False
        for w in app.windows():
            try:
                btns = [c for c in w.descendants(control_type="Button")
                        if (c.window_text() or "") == "Да"]
                if btns:
                    btns[0].click_input()
                    log.append("security Да clicked")
                    time.sleep(8)
                    done = True
                    break
            except Exception:
                continue
        if done:
            break
        time.sleep(3)
    snap(app, "before")
    wins = [w for w in app.windows() if w.window_text()]
    main_w = max(wins, key=lambda w: len(w.window_text()))
    log.append("MAIN WINDOW: " + main_w.window_text())
    ed = edits(main_w)
    log.append("поля ввода (%d):" % len(ed))
    for c, val, rect in ed:
        log.append("   y=%s h=%s val=%r" % (rect.top, rect.height(), (val or "")[:60]))
    hist = next((x for x in ed if "Диалог с нейросетью" in (x[1] or "")), None)
    log.append("история найдена: %s" % bool(hist))
    if hist:
        below = [x for x in ed if x[2].top > hist[2].top and x[2].height() < 100]
        target = below[0] if below else None
    else:
        target = ed[-1] if ed else None
    log.append("поле фразы: %s" % (bool(target)))
    if target:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(PHRASE, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        fld = target[0]
        fld.set_focus()
        time.sleep(1)
        fld.type_keys("^a", with_spaces=True)
        time.sleep(0.5)
        fld.type_keys("^v", with_spaces=True)
        log.append("фраза вставлена")
        time.sleep(30)
    snap(app, "after")
    ed2 = edits(main_w)
    for c, val, rect in ed2:
        log.append("ИТОГ y=%s h=%s val=%r" % (rect.top, rect.height(), (val or "")[:400]))
    try:
        img = main_w.capture_as_image()
        shot = OUT.with_name("chat_1c_screen.png")
        img.save(str(shot))
        log.append("скриншот: " + str(shot))
    except Exception as exc:
        log.append("скриншот не сделан: " + str(exc)[:120])
    log.append("1C ОСТАВЛЕН ОТКРЫТЫМ pid=%d" % p.pid)


try:
    main()
finally:
    OUT.write_text("\n".join(log), encoding="utf-8")
    print("записано:", OUT)
