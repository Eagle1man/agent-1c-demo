"""Проверка OPC UA-адаптера на тестовом стенде.

    py tools/check_opcua.py --endpoint opc.tcp://127.0.0.1:4841/demo

Читает те же узлы, что перечислены в agent/opcua_config.json, и печатает
значения. Стенд — только для проверки механизма: производственных данных в нём
нет, и в панели они не используются.
"""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "agent"))

from opcua_bridge import _read, load_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="opc.tcp://127.0.0.1:4841/demo")
    args = ap.parse_args()

    nodes = load_config().get("nodes") or {}
    try:
        values = asyncio.run(_read(args.endpoint, nodes, 8))
    except Exception as exc:                        # noqa: BLE001
        print("стенд недоступен:", type(exc).__name__, exc)
        return 2

    bad = [v for v in values if v.get("value") is None]
    for v in values:
        print(f"  {v['name']:26} {str(v.get('value')):>8} {v.get('unit','')}  "
              f"{v.get('quality')}  {v.get('alarm') or ''}")
    print(f"\nпрочитано {len(values) - len(bad)} из {len(values)}")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
