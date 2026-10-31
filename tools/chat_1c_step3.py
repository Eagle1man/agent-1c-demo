# -*- coding: utf-8 -*-
"""Шаг 3: закрыть диалог безопасности Win32-нажатием и прогнать фразу."""
import time
from pathlib import Path

OUT = Path(r"D:\agent-1c-demo\chat_1c_out3.txt")
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


def main():
    from pywinauto import Application, keyboard
    app = Application(backend="win32").connect(process=5336)
    log.append("win32 подключение: ок")
    for w in app.windows():
        try:
            log.append("WINDOW %r class=%s" % (w.window_text(), w.class_name()))
            for c in w.children():
                try:
                    log.append("   child %r class=%s" % (c.window_text(), c.class_name()))
                except Exception:
                    pass
        except Exception as exc:
            log.append("err " + str(exc)[:60])
    # 1) BM_CLICK по кнопке «Да»
    for w in app.windows():
        try:
            for c in w.children():
                try:
                    t = (c.window_text() or "").strip()
                    if t == "Да" and c.class_name() == "Button":
                        c.click()
                        log.append("BM_CLICK по Да выполнен")
                except Exception:
                    continue
        except Exception:
            continue
    time.sleep(4)
    app_u = Application(backend="uia").connect(process=5336)
    log.append("после BM_CLICK диалог: %s" % dialog_present(app_u))
    # 2) клавиатура: стрелка влево + Enter (по умолчанию фокус на «Нет»)
    for i in range(3):
        if not dialog_present(app_u):
            break
        keyboard.send_keys("{LEFT}")
        time.sleep(0.4)
        keyboard.send_keys("{ENTER}")
        time.sleep(3)
        log.append("попытка клавиатуры %d: диалог %s" % (i + 1, dialog_present(app_u)))
    # 3) если закрыт — работаем с полями
    if dialog_present(app_u):
        log.append("ДИАЛОГ НЕ ЗАКРЫТ — дальше нельзя")
        return
    time.sleep(6)
    w = None
    for cand in app_u.windows():
        try:
            if list(cand.descendants(control_type="Edit")):
                w = cand
                break
        except Exception:
            continue
    if w is None:
        log.append("окно с полями не найдено")
        return
    log.append("окно формы: %r" % (w.window_text() or ""))
    ed = []
    for c in w.descendants(control_type="Edit"):
        try:
            ed.append((c, c.get_value() or "", c.rectangle()))
        except Exception:
            pass
    ed.sort(key=lambda x: (x[2].top, x[2].left))
    for c, v, r in ed:
        log.append("ПОЛЕ y=%s h=%s val=%r" % (r.top, r.height(), v[:90]))
    hist = next((x for x in ed if "Диалог с нейросетью" in x[1]), None)
    if hist is None:
        hist = next((x for x in ed if x[2].height() > 100), None)
    log.append("история найдена: %s" % bool(hist))
    below = [x for x in ed if hist and x[2].top > hist[2].top]
    target = below[0] if below else None
    log.append("поле для фразы: %s" % bool(target))
    if target:
        import win32clipboard
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardText(PHRASE, win32clipboard.CF_UNICODETEXT)
        win32clipboard.CloseClipboard()
        f = target[0]
        f.set_focus()
        time.sleep(1)
        f.type_keys("{HOME}{DELETE}", with_spaces=True)
        f.type_keys("^v", with_spaces=True)
        time.sleep(1)
        log.append("после вставки значение поля: %r" % (f.get_value() or ""))
        time.sleep(35)
    ed2 = []
    for c in w.descendants(control_type="Edit"):
        try:
            ed2.append((c, c.get_value() or "", c.rectangle()))
        except Exception:
            pass
    ed2.sort(key=lambda x: x[2].top)
    for c, v, r in ed2:
        log.append("ИТОГ y=%s h=%s val=%r" % (r.top, r.height(), v[:700]))
    try:
        w.capture_as_image().save(r"D:\agent-1c-demo\chat_1c_screen3.png")
        log.append("скриншот 3 сохранён")
    except Exception as exc:
        log.append("скриншот: " + str(exc)[:80])


try:
    main()
finally:
    OUT.write_text("\n".join(log), encoding="utf-8")
    print("записано:", OUT)
