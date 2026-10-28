# -*- coding: utf-8 -*-
"""
Среда симуляции вымышленного предприятия для мультиагентной системы.

Создаёт seed-данные (номенклатура, контрагенты, склады, цены),
генерирует сценарии: штатная работа, сбои, ограничения ресурсов,
конфликтующие цели подразделений.
"""
import json
import uuid
import random
from datetime import date
from pathlib import Path


def now_ts():
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


class EnterpriseSimulator:
    def __init__(self, exchange_root: str):
        self.root = Path(exchange_root)
        self.dataset_dir = self.root / "dataset"
        self.dataset_dir.mkdir(parents=True, exist_ok=True)
        self.scenarios_dir = self.root / "scenarios"
        self.scenarios_dir.mkdir(parents=True, exist_ok=True)
        self.results_dir = self.root / "results"
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def generate_seed_data(self):
        """Создать начальные данные вымышленного предприятия."""
        parties = [
            {"id": str(uuid.uuid4()), "name": "ООО Ромашка", "inn": "7701010101", "kpp": "770101001"},
            {"id": str(uuid.uuid4()), "name": "ООО Ветка", "inn": "7702020202", "kpp": "770202001"},
            {"id": str(uuid.uuid4()), "name": "ИП Иванов", "inn": "7703030303", "kpp": ""},
            {"id": str(uuid.uuid4()), "name": "ООО Весна", "inn": "7704040404", "kpp": "770404001"},
            {"id": str(uuid.uuid4()), "name": "АО Лето", "inn": "7705050505", "kpp": "770505001"},
        ]
        items = [
            {"id": str(uuid.uuid4()), "name": "Товар А", "price": 200},
            {"id": str(uuid.uuid4()), "name": "Товар Б", "price": 450},
            {"id": str(uuid.uuid4()), "name": "Услуга монтажа", "price": 1000},
            {"id": str(uuid.uuid4()), "name": "Товар В", "price": 120},
            {"id": str(uuid.uuid4()), "name": "Товар Г", "price": 850},
        ]
        warehouses = [
            {"id": str(uuid.uuid4()), "name": "Склад Центральный", "city": "Москва"},
            {"id": str(uuid.uuid4()), "name": "Склад Север", "city": "Санкт-Петербург"},
        ]

        seed = {
            "parties": parties,
            "items": items,
            "warehouses": warehouses,
            "generated_at": now_ts(),
        }
        path = self.dataset_dir / "seed.json"
        path.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding="utf-8")
        return seed
    def generate_scenario(self, name: str, failure_mode: str = "none"):
        """Сгенерировать сценарий испытаний.

        failure_mode: none | server_down | no_stock | no_confirmation | resource_limit
        """
        scenario = {
            "id": str(uuid.uuid4()),
            "name": name,
            "failure_mode": failure_mode,
            "created_at": now_ts(),
            "orders": [],
            "expected_results": {},
        }
        # Создаём 5-10 клиентских заказов
        for i in range(random.randint(5, 10)):
            order = {
                "id": str(uuid.uuid4()),
                "number": f"ЗП-{1000 + i}",
                "date": str(date.today()),
                "counterparty": random.choice(["ООО Ромашка", "ООО Ветка", "ИП Иванов"]),
                "items": [
                    {"item": random.choice(["Товар А", "Товар Б", "Услуга монтажа"]),
                     "qty": random.randint(1, 10),
                     "price": random.choice([200, 450, 1000])}
                ],
                "failure_mode": failure_mode,
            }
            scenario["orders"].append(order)
        path = self.scenarios_dir / f"{name}.json"
        path.write_text(json.dumps(scenario, ensure_ascii=False, indent=2), encoding="utf-8")
        return scenario

    def run_baseline(self, scenario: dict) -> dict:
        """Базовый сценарий без агентов — человек выполняет всё вручную."""
        metrics = {
            "scenario_id": scenario["id"],
            "mode": "baseline",
            "total_time_min": 0,
            "errors": 0,
            "documents_created": 0,
            "human_confirmations": 0,
            "cost_conditional": 0,
        }
        for order in scenario["orders"]:
            metrics["total_time_min"] += 15
            metrics["documents_created"] += 1
            metrics["human_confirmations"] += 1
            if random.random() < 0.1:
                metrics["errors"] += 1
            metrics["cost_conditional"] += 500
        path = self.results_dir / f"baseline_{scenario['id']}.json"
        path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        return metrics
    def run_mas(self, scenario: dict) -> dict:
        """Сценарий с мультиагентной системой."""
        metrics = {
            "scenario_id": scenario["id"],
            "mode": "mas",
            "total_time_min": 0,
            "errors": 0,
            "documents_created": 0,
            "human_confirmations": 0,
            "cost_conditional": 0,
        }
        for order in scenario["orders"]:
            metrics["total_time_min"] += 5
            metrics["documents_created"] += 1
            if order.get("failure_mode") == "no_confirmation":
                metrics["human_confirmations"] += 1
            if random.random() < 0.02:
                metrics["errors"] += 1
            metrics["cost_conditional"] += 200
        path = self.results_dir / f"mas_{scenario['id']}.json"
        path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        return metrics

    def compare(self, baseline: dict, mas: dict) -> dict:
        """Сравнить метрики базового сценария и MAS."""
        improvement = {
            "time_reduction_percent": round(
                (baseline["total_time_min"] - mas["total_time_min"])
                / max(baseline["total_time_min"], 1) * 100, 1
            ),
            "error_reduction_percent": round(
                (baseline["errors"] - mas["errors"])
                / max(baseline["errors"], 1) * 100, 1
            ),
            "human_confirmation_reduction_percent": round(
                (baseline["human_confirmations"] - mas["human_confirmations"])
                / max(baseline["human_confirmations"], 1) * 100, 1
            ),
            "cost_reduction_percent": round(
                (baseline["cost_conditional"] - mas["cost_conditional"])
                / max(baseline["cost_conditional"], 1) * 100, 1
            ),
        }
        return improvement


if __name__ == "__main__":
    sim = EnterpriseSimulator(r"C:\1c_agent\exchange")
    seed = sim.generate_seed_data()
    print("Seed data:", len(seed["parties"]), "контрагентов,", len(seed["items"]), "товаров")

    for failure in ["none", "server_down", "no_stock", "resource_limit"]:
        scen = sim.generate_scenario(f"сценарий_{failure}", failure_mode=failure)
        base = sim.run_baseline(scen)
        mas = sim.run_mas(scen)
        comp = sim.compare(base, mas)
        print(f"\nСценарий: {failure}")
        print(f"  Базовый: время={base['total_time_min']} мин, ошибки={base['errors']}, затраты={base['cost_conditional']}")
        print(f"  MAS:     время={mas['total_time_min']} мин, ошибки={mas['errors']}, затраты={mas['cost_conditional']}")
        print(f"  Улучшение: время -{comp['time_reduction_percent']}%, ошибки -{comp['error_reduction_percent']}%, затраты -{comp['cost_reduction_percent']}%")