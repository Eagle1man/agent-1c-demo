"""Список endpoint'ов OPC UA сервера (до создания сессии).

    py tools/opcua_endpoints.py --endpoint opc.tcp://127.0.0.1:4840

Показывает политики безопасности и режимы авторизации: по ним видно, пускает
ли сервер анонимно и нужен ли сертификат. Это первый шаг интеграции, когда
параметры сервера ещё не переданы.
"""
import argparse
import asyncio

from asyncua import Client


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="opc.tcp://127.0.0.1:4840")
    args = ap.parse_args()

    client = Client(url=args.endpoint, timeout=10)
    try:
        endpoints = await client.connect_and_get_server_endpoints()
    except Exception as exc:                        # noqa: BLE001
        print("не удалось получить endpoints:", type(exc).__name__, exc)
        return 2
    for ep in endpoints:
        print("url:", ep.EndpointUrl)
        print("  security:", ep.SecurityPolicyUri)
        print("  mode:", ep.SecurityMode)
        print("  user tokens:", [t.PolicyId for t in (ep.UserIdentityTokens or [])])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
