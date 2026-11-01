"""Просмотр адресного пространства OPC UA: что реально доступно на сервере.

    py tools/opcua_browse.py --endpoint opc.tcp://127.0.0.1:4840

Печатает дерево объектов (глубина 3) и значения переменных. Нужен, чтобы
получить список узлов от сервера, а не придумывать NodeId.
"""
import argparse
import asyncio

from asyncua import Client, ua


async def walk(node, depth, max_depth, lines, limit):
    if depth > max_depth or len(lines) > limit:
        return
    try:
        children = await node.get_children()
    except Exception as exc:                        # noqa: BLE001
        lines.append("  " * depth + f"!! {exc}")
        return
    for child in children:
        try:
            name = await child.read_browse_name()
            nid = child.node_id
            cls = await child.read_node_class()
        except Exception as exc:                    # noqa: BLE001
            lines.append("  " * depth + f"!! {exc}")
            continue
        label = f"{'  ' * depth}{name.Name}  [{cls.name}]  {nid}"
        if cls == ua.NodeClass.Variable:
            try:
                value = await child.read_value()
                label += f"  = {value!r}"
            except Exception:                       # noqa: BLE001
                label += "  = <нет значения>"
        lines.append(label)
        if len(lines) > limit:
            return
        await walk(child, depth + 1, max_depth, lines, limit)


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", default="opc.tcp://127.0.0.1:4840")
    ap.add_argument("--depth", type=int, default=3)
    ap.add_argument("--limit", type=int, default=200)
    args = ap.parse_args()

    async with Client(url=args.endpoint, timeout=10) as client:
        root = client.nodes.objects
        lines = [f"endpoint: {args.endpoint}"]
        await walk(root, 0, args.depth, lines, args.limit)
    print("\n".join(lines[: args.limit + 1]))


if __name__ == "__main__":
    asyncio.run(main())
