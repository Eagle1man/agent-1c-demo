"""Нажать «Да» в предупреждении безопасности 1С (по pid).

click_input требует фокуса и в фоне не срабатывает; UIA invoke работает
без активации окна.
"""
import sys

from pywinauto import Application

pid = int(sys.argv[1])
app = Application(backend="uia").connect(process=pid, timeout=20)
clicked = 0
for w in app.windows():
    try:
        for c in w.descendants(control_type="Button"):
            if (c.window_text() or "").strip() != "Да":
                continue
            for action in ("invoke", "click", "click_input"):
                try:
                    getattr(c, action)()
                    clicked += 1
                    print("нажато:", action)
                    break
                except Exception as exc:            # noqa: BLE001
                    last = exc
            else:
                print("не удалось нажать:", last)
    except Exception as exc:                        # noqa: BLE001
        print("окно:", exc)
print("итого нажатий:", clicked)
