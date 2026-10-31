"""Автоматический прогон моста в 1С без участия человека.

Запускает 1С с обработкой, ждёт, ловит окно ошибки, нажимает «Сформировать
отчет об ошибке» и печатает содержимое отчёта. Нужен, чтобы не гонять
человека за скриншотами: цикл «собрал → запустил → прочитал ошибку» должен
занимать минуту.

Коды возврата: 0 — форма открылась (мост работает), 2 — ошибка (напечатана),
3 — не удалось определить состояние.
"""
import glob
import json
import subprocess
import sys
import time
import zipfile
from pathlib import Path

EXE = r"C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe"
BASE = r"C:\1c_bases\DemoAgent"
EPF = r"C:\1c_bases\AgentMost_fixed.epf"
REPORT_DIRS = [
    r"C:\Users\diorl\OneDrive\Рабочий стол",
    r"C:\Users\diorl\OneDrive\Рабочий стол\дело 1",
    r"C:\Users\diorl\Desktop",
]


def newest_report(after_ts):
    files = []
    for d in REPORT_DIRS:
        files.extend(glob.glob(str(Path(d) / "Ошибка_*.zip")))
    files = [f for f in files if Path(f).stat().st_mtime >= after_ts - 5]
    return max(files, key=lambda f: Path(f).stat().st_mtime) if files else None


def parse_report(path):
    with zipfile.ZipFile(path) as z:
        data = json.loads(z.read("report.json").decode("utf-8"))
    errs = data.get("errorInfo", {}).get("applicationErrorInfo", {}).get("errors", [])
    out = []
    for e in errs:
        for item in e:
            if item and not str(item).startswith("["):
                out.append(str(item))
    return out


def main():
    from pywinauto import Application

    started = time.time()
    proc = subprocess.Popen([EXE, "ENTERPRISE", "/F", BASE,
                             "/Execute", EPF, "/DisableStartupDialogs"])
    print(f"запущен 1С pid={proc.pid}")
    time.sleep(20)

    try:
        app = Application(backend="uia").connect(process=proc.pid, timeout=30)
    except Exception as exc:                       # noqa: BLE001
        print("НЕ УДАЛОСЬ ПОДКЛЮЧИТЬСЯ:", exc)
        return 3

    deadline = time.time() + 90
    confirmed = False
    while time.time() < deadline:
        clicked = False
        texts = []
        try:
            for w in app.windows():
                for c in w.descendants():
                    try:
                        ct = c.element_info.control_type
                        t = (c.window_text() or "").strip()
                    except Exception:               # noqa: BLE001
                        continue
                    if ct == "Text" and t:
                        texts.append(t)
        except Exception:                           # noqa: BLE001
            pass
        blob_now = " ".join(texts)
        if ("Предупреждение безопасности" in blob_now) and not confirmed:
            # Один Enter — и больше клавиш не шлём: иначе Enter попадает в форму
            # и нажимает кнопку по умолчанию (форма закрывается).
            try:
                from pywinauto.keyboard import send_keys
                top = max((x for x in app.windows() if x.window_text()),
                          key=lambda x: len(x.window_text()))
                top.set_focus()
                send_keys("{ENTER}", pause=0.1)
                confirmed = True
                time.sleep(5)
                continue
            except Exception:                       # noqa: BLE001
                pass
        if "Фраза" in blob_now or "ПутьКExchange" in blob_now:
            break
        if "непредвиденная ошибка" in blob_now.lower():
            break
        time.sleep(2)

    time.sleep(4)
    texts = []
    for w in app.windows():
        try:
            texts.extend(c.window_text() for c in w.descendants(control_type="Text")
                         if c.window_text())
        except Exception:                           # noqa: BLE001
            pass
    blob = " ".join(texts)

    if "непредвиденная ошибка" in blob.lower():
        print("ОШИБКА ПРИ ОТКРЫТИИ — запрашиваю отчёт")
        for w in app.windows():
            try:
                for c in w.descendants(control_type="Hyperlink"):
                    if "отчет об ошибке" in (c.window_text() or "").lower():
                        c.click_input()
                        break
            except Exception:                       # noqa: BLE001
                pass
        time.sleep(6)
        rep = newest_report(started)
        if rep:
            print("отчёт:", rep)
            for line in parse_report(rep):
                print("  ", line)
        else:
            print("отчёт не найден")
        try:
            proc.kill()
        except Exception:                           # noqa: BLE001
            pass
        return 2

    if "Фраза" in blob or "ПутьКExchange" in blob:
        print("ФОРМА ОТКРЫТА — мост должен опрашивать exchange")
        for t in texts[:12]:
            print("  |", t[:120])
        print("1С оставлена запущенной")
        return 0

    print("ФОРМА НЕ ОТКРЫЛАСЬ: полей формы (ПутьКExchange/Фраза) нет")
    for t in texts[:20]:
        print("  |", t[:120])
    return 3


if __name__ == "__main__":
    sys.exit(main())
