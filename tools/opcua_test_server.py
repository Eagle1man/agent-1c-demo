# -*- coding: utf-8 -*-
"""Тестовый OPC UA сервер для демонстрации (НЕ производственный).

Зачем: у предприятия OPC UA сервер есть, но его endpoint и узлы ещё не переданы.
Чтобы панель предприятия и агенты работали уже сейчас, поднимаем локальный
сервер с теми же типами данных: температура, давление, уровень, счётчик выпуска,
авария линии. Переключение на реальный сервер — правка `agent/opcua_config.json`,
код адаптера не меняется.

Запуск:
    py tools/opcua_test_server.py --port 4840
Значения меняются по кругу, чтобы на демо было видно обновление.
"""
import argparse
import asyncio
import math
import time

from asyncua import Server, ua

NODES = {
    # имя узла: (описание, единица, минимум аварии, максимум аварии)
    "Температура": ("Температура линии", "°C", 18.0, 85.0),
    "Давление": ("Давление в контуре", "бар", 2.0, 8.0),
    "Уровень": ("Уровень в резервуаре", "%", 15.0, 95.0),
    "Выпуск": ("Счётчик выпуска", "шт", None, None),
    "Авария": ("Аварийный сигнал линии", "", None, None),
}


async def main(port: int):
    server = Server()
    await server.init()
    server.set_endpoint(f"opc.tcp://127.0.0.1:{port}/demo")
    server.set_server_name("OPC UA демо-стенд (тестовые данные)")
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    idx = await server.register_namespace("http://example.org/enterprise/demo")

    objects = server.nodes.objects
    line = await objects.add_object(idx, "Линия1")
    nodes = {}
    for name in NODES:
        dtype = ua.VariantType.Boolean if name == "Авария" else ua.VariantType.Double
        # Идентификаторы как на реальном объекте: ns=2;s=Линия1.<Параметр>
        node_id = ua.NodeId(f"Линия1.{name}", idx)
        nodes[name] = await line.add_variable(node_id, name, 0.0, dtype)
        await nodes[name].set_writable()

    print(f"OPC UA тестовый сервер: opc.tcp://127.0.0.1:{port}/demo")
    print("узлы:", ", ".join(f"ns={idx};s=Линия1.{n}" for n in NODES))

    async with server:
        t0 = time.time()
        while True:
            t = time.time() - t0
            await nodes["Температура"].write_value(ua.DataValue(
                ua.Variant(60 + 12 * math.sin(t / 20), ua.VariantType.Double)))
            await nodes["Давление"].write_value(ua.DataValue(
                ua.Variant(5 + 1.8 * math.sin(t / 13 + 1), ua.VariantType.Double)))
            await nodes["Уровень"].write_value(ua.DataValue(
                ua.Variant(55 + 30 * math.sin(t / 37), ua.VariantType.Double)))
            await nodes["Выпуск"].write_value(ua.DataValue(
                ua.Variant(float(int(t / 5)), ua.VariantType.Double)))
            # Авария включается на 10 секунд каждую минуту — видно на панели
            await nodes["Авария"].write_value(ua.DataValue(
                ua.Variant((t % 60) > 50, ua.VariantType.Boolean)))
            await asyncio.sleep(2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=4841)
    args = ap.parse_args()
    try:
        asyncio.run(main(args.port))
    except KeyboardInterrupt:
        print("остановлен")
