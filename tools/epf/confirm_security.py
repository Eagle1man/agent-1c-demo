"""Подтвердить предупреждение безопасности 1С клавиатурой (Enter / Alt+Да).

UIA invoke на этой кнопке не срабатывает: диалог остаётся. Поэтому пробуем
фокус + Enter, затем Space, затем горячую клавишу.
"""
import sys
import time

from pywinauto import Application
from pywinauto.keyboard import send_keys

pid = int(sys.argv[1])
app = Application(backend="uia").connect(process=pid, timeout=20)

for attempt in range(4):
    wins = [w for w in app.windows() if w.window_text()]
    if not wins:
        break
    w = max(wins, key=lambda x: len(x.window_text()))
    try:
        w.set_focus()
    except Exception as exc:                        # noqa: BLE001
        print("focus:", exc)
    time.sleep(1)
    for keys in ("{ENTER}", " ", "{TAB}{ENTER}"):
        try:
            send_keys(keys, pause=0.1)
        except Exception as exc:                    # noqa: BLE001
            print("keys:", keys, exc)
        time.sleep(2)
    texts = []
    try:
        texts = [c.window_text() for c in w.descendants(control_type="Text")
                 if c.window_text()]
    except Exception:                               # noqa: BLE001
        pass
    if not any("Предупреждение безопасности" in t for t in texts):
        print("предупреждение закрыто, попытка", attempt + 1)
        break
else:
    print("предупреждение всё ещё на экране")
