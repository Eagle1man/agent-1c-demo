"""Запуск демо одной командой: 1С с мостом + панель предприятия.

    py tools/run_demo.py

Что делает:
1. если 1С с мостом не запущена — запускает и подтверждает предупреждение
   безопасности сам;
2. если панель не отвечает — поднимает её в отдельном процессе;
3. печатает адрес и подсказки для показа.

Останавливать: закрыть окно 1С и `py tools/panel_pid.py --kill`.
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PANEL = "http://127.0.0.1:8077"
PY = sys.executable


def panel_alive(timeout=3):
    try:
        with urllib.request.urlopen(PANEL + "/api/health", timeout=timeout) as r:
            return json.loads(r.read())
    except Exception:                               # noqa: BLE001
        return None


def one_c_running():
    out = subprocess.run(["tasklist"], capture_output=True, text=True,
                         encoding="cp866").stdout
    return "1cv8t.exe" in out.lower() or "1cv8ct.exe" in out.lower()


def main():
    if not one_c_running():
        print("1С не запущена — запускаю мост…")
        subprocess.run([PY, str(ROOT / "tools" / "epf" / "test_epf_live.py")])
    else:
        print("1С уже запущена")

    health = panel_alive()
    if not health:
        print("панель не отвечает — запускаю…")
        subprocess.Popen([PY, str(ROOT / "agent" / "panel_server.py"),
                          "--port", "8077"],
                         cwd=str(ROOT),
                         creationflags=subprocess.CREATE_NEW_CONSOLE)
        for _ in range(15):
            time.sleep(2)
            health = panel_alive()
            if health:
                break

    print("\n" + "=" * 60)
    if health and health.get("status") == "ok":
        print("готово. панель:", PANEL)
        print("мост:", health.get("bridge"), "· 1С отвечает")
    else:
        print("панель:", PANEL, "· 1С пока не отвечает:", (health or {}).get("error"))
        print("проверьте окно 1С: обработка должна быть открыта")
    print("=" * 60)
    print("\nСценарий показа (5 минут): см. docs/DEMO.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
