# -*- coding: utf-8 -*-
"""Шаг 2: закрыть диалог безопасности у ЖИВОЙ 1С и прогнать фразу в окне диалога."""
import time
from pathlib import Path

OUT = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\chat_1c_out2.txt")
PHRASE = "покажи задолженность контрагентов"
log = []


def main():
    from pywinauto import Application, Desktop
    app = None
    for pid in [5336]:
        try:
            app = Application(backend="uia").connect(process=pid)
            log.append("подключился к pid=%d" % pid)
        except Exception as exc:
            log.append("pid %d: %s" % (pid, exc))
    if app is None:
        log.append("не подключился")
        return
    for w in app.windows():
        try:
            log.append("WINDOW: %r" % (w.window_text() or ""))
            for b in w.descendants(control_type="Button"):
                try:
                    log.append("   Button %r" % (b.window_text() or ""))
                except Exception:
                    pass
        except Exception as exc:
            log.append("err: " + str(exc)[:80])
    # закрываем диалог: сначала Invoke, затем клик
    for attempt in range(6):
        clicked = False
        for w in app.windows():
            try:
                for b in w.descendants(control_type="Button"):
                    t = (b.window_text() or "").strip()
                    if t.startswith("Да"):
                        try:
                            b.invoke()
                            log.append("invoke Да: ок")
                        except Exception as exc:
                            log.append("invoke не сработал: " + str(exc)[:60])
                            b.click_input()
                            log.append("click Да: ок")
                        clicked = True
                        break
            except Exception:
                continue
            if clicked:
                break
        time.sleep(4)
        # проверяем, остался ли текст диалога
        still = False
        for w in app.windows():
            try:
                for t in w.descendants(control_type="Text"):
                    if "Предупреждение безопасности" in (t.window_text() or ""):
                        still = True
                        break
            except Exception:
                continue
            if still:
                break
        log.append("попытка %d: диалог %s" % (attempt + 1, "ещё здесь" if still else "закрыт"))
        if not still:
            break
    time.sleep(6)
    # ищем окно обработки и поля
    target_w = None
    for w in app.windows():
        try:
            for e in w.descendants(control_type="Edit"):
                target_w = w
                break
        except Exception:
            continue
        if target_w is not None:
            break
    if target_w is None:
        log.append("полей ввода не найдено")
        return
    log.append("окно с полями: %r" % (target_w.window_text() or ""))
    ed = []
    for c in target_w.descendants(control_type="Edit"):
        try:
            ed.append((c, c.get_value() or "", c.rectangle()))
        except Exception:
            pass
    ed.sort(key=lambda x: (x[2].top, x[2].left))
    for c, v, r in ed:
        log.append("ПОЛЕ y=%s h=%s val=%r" % (r.top, r.height(), v[:80]))
    hist = next((x for x in ed if "Диалог с нейросетью" in x[1]), None)
    if hist is None:
        hist = next((x for x in ed if x[2].height() > 100), None)
    log.append("поле истории: %s" % bool(hist))
    below = [x for x in ed if hist and x[2].top > hist[2].top]
    target = below[0] if below else (ed[0] if ed else None)
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
        log.append("фраза вставлена в поле y=%s" % target[2].top)
        time.sleep(35)
    ed2 = []
    for c in target_w.descendants(control_type="Edit"):
        try:
            ed2.append((c, c.get_value() or "", c.rectangle()))
        except Exception:
            pass
    ed2.sort(key=lambda x: x[2].top)
    for c, v, r in ed2:
        log.append("ИТОГ y=%s h=%s val=%r" % (r.top, r.height(), v[:600]))
    try:
        target_w.capture_as_image().save(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo\chat_1c_screen2.png")
        log.append("скриншот 2 сохранён")
    except Exception as exc:
        log.append("скриншот: " + str(exc)[:80])


try:
    main()
finally:
    OUT.write_text("\n".join(log), encoding="utf-8")
    print("записано:", OUT)
