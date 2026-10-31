# -*- coding: utf-8 -*-
"""Живой тест окна диалога: запуск 1С, снятие диалога безопасности,
вставка фразы в поле и чтение истории ответов."""
import subprocess
import time
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
BASE = r"C:\1c_bases\DemoAgentT"
EPF = r"C:\1c_bases\AgentMost.epf"
DIR = Path(r"D:\agent-1c-demo")
OUT = DIR / "chat_live_out.txt"
PHRASE = "покажи задолженность контрагентов"
log = []


def dialog_present(app):
    for w in app.windows():
        try:
            for t in w.descendants(control_type="Text"):
                if "Предупреждение безопасности" in (t.window_text() or ""):
                    return True
        except Exception:
            continue
    return False


def err_present(app):
    for w in app.windows():
        try:
            for t in w.descendants(control_type="Text"):
                if "непредвиденная" in (t.window_text() or ""):
                    return True
        except Exception:
            continue
    return False


def all_edits(app):
    res = []
    for w in app.windows():
        try:
            for c in w.descendants(control_type="Edit"):
                try:
                    res.append((c, c.get_value() or "", c.rectangle(), w.window_text() or ""))
                except Exception:
                    pass
        except Exception:
            continue
    return res


def main():
    from pywinauto import Application, keyboard
    p = subprocess.Popen([EXE, "ENTERPRISE", "/F", BASE, "/Execute", EPF,
                          "/DisableStartupDialogs"])
    log.append("1C pid=%d" % p.pid)
    time.sleep(45)
    app = Application(backend="uia").connect(process=p.pid)
    for i in range(10):
        if not dialog_present(app):
            break
        keyboard.send_keys("{LEFT}")
        time.sleep(0.4)
        keyboard.send_keys("{ENTER}")
        time.sleep(3)
        log.append("снятие диалога, попытка %d: %s" % (i + 1, dialog_present(app)))
    time.sleep(10)
    log.append("ошибка формы: %s" % err_present(app))
    ed = all_edits(app)
    log.append("полей ввода: %d" % len(ed))
    for c, v, r, title in ed:
        log.append("ПОЛЕ win=%r y=%s h=%s val=%r" % (title[:20], r.top, r.height(), v[:90]))
    hist = next((x for x in ed if "Диалог с нейросетью" in x[1]), None)
    if hist is None:
        hist = next((x for x in ed if x[2].height() > 100), None)
    log.append("история найдена: %s" % bool(hist))
    if hist is not None:
        below = [x for x in ed if x[2].top > hist[2].top and x[2].height() < 200]
        target = below[0] if below else None
    else:
        target = None
    log.append("поле фразы найдено: %s" % bool(target))
    if target:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(PHRASE, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        f = target[0]
        f.set_focus()
        time.sleep(1)
        f.type_keys("^a", with_spaces=True)
        time.sleep(0.5)
        f.type_keys("^v", with_spaces=True)
        time.sleep(1)
        log.append("значение поля после вставки: %r" % (f.get_value() or ""))
        time.sleep(45)
    for c, v, r, title in all_edits(app):
        log.append("ИТОГ y=%s h=%s val=%r" % (r.top, r.height(), v[:900]))
    try:
        wins = [w for w in app.windows() if w.window_text()]
        w = max(wins, key=lambda x: x.rectangle().width())
        w.capture_as_image().save(str(DIR / "chat_live_screen.png"))
        log.append("скриншот сохранён")
    except Exception as exc:
        log.append("скриншот: " + str(exc)[:90])
    log.append("1C оставлена открытой pid=%d" % p.pid)


try:
    main()
finally:
    OUT.write_text("\n".join(log), encoding="utf-8")
    print("записано", OUT)
