# -*- coding: utf-8 -*-
"""Чтение производственных данных по OPC UA (только чтение, только белый список).

Правила, из которых сделан модуль:
- читаются ТОЛЬКО узлы из `agent/opcua_config.json`; запись методов не реализована
  вовсе (ТЗ §11.1, §11.2) — категория C отключена на уровне кода;
- отказ источника возвращается как `available: False` с текстом ошибки, а не как
  пустые значения: «нет связи» и «все датчики в норме» — разные утверждения;
- у каждого значения — время чтения и качество от сервера.

Запуск для проверки:
    py agent/opcua_bridge.py
"""
import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "opcua_config.json"


def now_ts():
    return datetime.now().isoformat(timespec="seconds")


def load_config():
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


async def _read(endpoint, nodes, timeout, username="", password="", security_string=""):
    from asyncua import Client

    client = Client(url=endpoint, timeout=timeout)
    if security_string:
        # Для реального сервера: "Basic256Sha256,SignAndEncrypt,cert.pem,key.pem".
        # Сертификат клиента должен быть доверен на сервере — это действие человека.
        client.set_security_string(security_string)
    if username:
        client.set_user(username)
        client.set_password(password)
    result = []
    async with client:
        for key, cfg in nodes.items():
            item = {"key": key, "name": cfg.get("name", key),
                    "unit": cfg.get("unit", ""), "node_id": cfg.get("node_id")}
            try:
                node = client.get_node(cfg["node_id"])
                dv = await node.read_data_value()
                value = dv.Value.Value
                quality = str(dv.StatusCode.name) if dv.StatusCode else "Unknown"
                item.update({
                    "value": value if not isinstance(value, (bytes, bytearray)) else None,
                    "quality": quality,
                    "source_ts": dv.SourceTimestamp.isoformat(timespec="seconds")
                    if dv.SourceTimestamp else None,
                    "alarm": None,
                })
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    lo, hi = cfg.get("min"), cfg.get("max")
                    if lo is not None and value < lo:
                        item["alarm"] = f"ниже минимума ({lo})"
                    elif hi is not None and value > hi:
                        item["alarm"] = f"выше максимума ({hi})"
            except Exception as exc:                # noqa: BLE001
                item.update({"value": None, "quality": "Bad",
                             "error": f"{type(exc).__name__}: {exc}"[:160]})
            result.append(item)
    return result


def read_all():
    """Прочитать все узлы. Без сервера — available=False, без выдуманных чисел."""
    cfg = load_config()
    endpoint = cfg.get("endpoint")
    nodes = cfg.get("nodes") or {}
    if not endpoint or not nodes:
        return {"available": False, "ts": now_ts(), "source": "OPC UA",
                "error": "не настроен endpoint или список узлов"}
    started = time.time()
    try:
        values = asyncio.run(_read(
            endpoint, nodes, float(cfg.get("timeout_sec") or 8),
            cfg.get("username") or "", cfg.get("password") or "",
            cfg.get("security_string") or ""))
    except Exception as exc:                        # noqa: BLE001
        return {"available": False, "ts": now_ts(), "source": "OPC UA",
                "endpoint": endpoint,
                "error": f"{type(exc).__name__}: {exc}"[:200],
                "elapsed_ms": int((time.time() - started) * 1000)}
    return {
        "available": True,
        "ts": now_ts(),
        "source": "OPC UA",
        "endpoint": endpoint,
        "elapsed_ms": int((time.time() - started) * 1000),
        "values": values,
        "alarms": [v for v in values if v.get("alarm")],
    }


if __name__ == "__main__":
    data = read_all()
    print(json.dumps(data, ensure_ascii=False, indent=2))
