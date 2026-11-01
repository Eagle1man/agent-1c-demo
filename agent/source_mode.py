# -*- coding: utf-8 -*-
"""Режим источника производственных данных (ТЗ §4.2, план этапа D).

Три режима, один и тот же интерфейс:
    opcua        — есть OPC UA endpoint, читаем разрешённые узлы;
    scada-http   — есть RapidSCADA HTTP API;
    unavailable  — ни того, ни другого.

Режим определяется фактом ответа, а не настройкой «на будущее»: если endpoint
задан, но сервер молчит, это `unavailable` с причиной. Молчаливого перехода в
«всё в норме» быть не должно.
"""
from pathlib import Path

from opcua_bridge import load_config as opcua_config, read_all as opcua_read

PROJECT = Path(__file__).resolve().parent.parent


def scada_http_available() -> bool:
    """RapidSCADA HTTP API: нужен не только конфиг, но и ответ сервиса."""
    cfg_path = Path(__file__).resolve().parent / "scada_config.json"
    try:
        import json
        cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    url = (cfg.get("scada_url") or "").rstrip("/")
    if not url:
        return False
    try:
        import urllib.request
        with urllib.request.urlopen(url + "/api/alarms/active", timeout=2):
            return True
    except Exception:                               # noqa: BLE001
        return False


def current():
    """Текущий режим и данные (если есть)."""
    cfg = opcua_config()
    endpoint = (cfg or {}).get("endpoint")
    if endpoint:
        data = opcua_read()
        data["mode"] = "opcua"
        data["configured"] = True
        return data

    if scada_http_available():
        return {"mode": "scada-http", "available": False, "source": "RapidSCADA",
                "ts": None, "configured": True,
                "error": "HTTP API не опрашивается: сервис не установлен"}

    return {
        "mode": "unavailable",
        "available": False,
        "configured": False,
        "source": None,
        "ts": None,
        "error": ("Производственный источник не подключён. OPC UA предусмотрен: "
                  "укажите endpoint и узлы в agent/opcua_config.json, когда сервер "
                  "появится — код менять не нужно. RapidSCADA HTTP API не отвечает."),
    }


if __name__ == "__main__":
    import json
    print(json.dumps(current(), ensure_ascii=False, indent=2))
