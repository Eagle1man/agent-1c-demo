"""Запуск внешней обработки 1С в предприятии и ожидание завершения.

Нужен для разовых обработок (наполнение базы, служебные скрипты): запускает
1С с /Execute, подтверждает предупреждение безопасности (фокус + Enter),
ждёт выхода процесса и печатает результат.

Запуск:
    py tools/run_epf.py C:\\1c_bases\\SeedData2.epf --wait 600
"""
import argparse
import subprocess
import sys
import time

from pywinauto import Application
from pywinauto.keyboard import send_keys

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"


def confirm_security(app):
    for _ in range(30):
        texts = []
        try:
            for w in app.windows():
                for c in w.descendants(control_type="Text"):
                    t = c.window_text()
                    if t:
                        texts.append(t)
        except Exception:                           # noqa: BLE001
            pass
        if any("Предупреждение безопасности" in t for t in texts):
            try:
                top = max((x for x in app.windows() if x.window_text()),
                          key=lambda x: len(x.window_text()))
                top.set_focus()
                send_keys("{ENTER}", pause=0.1)
                return True
            except Exception:                       # noqa: BLE001
                pass
        time.sleep(2)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("epf")
    ap.add_argument("--base", default=r"C:\1c_bases\DemoAgent")
    ap.add_argument("--wait", type=int, default=600)
    args = ap.parse_args()

    proc = subprocess.Popen([EXE, "ENTERPRISE", "/F", args.base,
                             "/Execute", args.epf, "/DisableStartupDialogs"])
    print(f"запущен 1С pid={proc.pid}, обработка: {args.epf}")

    time.sleep(15)
    try:
        app = Application(backend="uia").connect(process=proc.pid, timeout=30)
        if confirm_security(app):
            print("предупреждение безопасности подтверждено")
        else:
            print("предупреждения не было")
    except Exception as exc:                        # noqa: BLE001
        print("подключиться к окну не удалось:", exc)

    start = time.time()
    while time.time() - start < args.wait:
        if proc.poll() is not None:
            print(f"обработка завершилась, код {proc.returncode}, "
                  f"время {time.time() - start:.0f} с")
            return 0
        time.sleep(5)

    print(f"обработка не завершилась за {args.wait} с — процесс оставлен")
    return 3


if __name__ == "__main__":
    sys.exit(main())
