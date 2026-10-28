# -*- coding: utf-8 -*-
"""
Инструмент экспериментальной валидации мультиагентной системы.

Запускает серию экспериментов: базовый сценарий vs сценарий с агентами.
Собирает метрики: время, качество (ошибки), затраты, человеческие подтверждения.
Формирует итоговый отчёт.
"""
import sys
import json
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from simulator import EnterpriseSimulator


def run_experiments(exchange_root: str, n_scenarios: int = 10):
    sim = EnterpriseSimulator(exchange_root)
    sim.generate_seed_data()

    failures = ["none", "server_down", "no_stock", "resource_limit", "no_confirmation"]
    results = []

    for i in range(n_scenarios):
        failure = failures[i % len(failures)]
        scen = sim.generate_scenario(f"эксперимент_{i:02d}", failure_mode=failure)
        base = sim.run_baseline(scen)
        mas = sim.run_mas(scen)
        comp = sim.compare(base, mas)
        results.append({
            "scenario": scen["name"],
            "failure_mode": failure,
            "baseline": base,
            "mas": mas,
            "improvement": comp,
        })

    # Итоговый отчёт
    report = {
        "generated_at": sim.now_ts() if hasattr(sim, "now_ts") else "",
        "n_scenarios": n_scenarios,
        "results": results,
        "summary": {
            "avg_time_reduction": round(
                sum(r["improvement"]["time_reduction_percent"] for r in results) / n_scenarios, 1
            ),
            "avg_error_reduction": round(
                sum(r["improvement"]["error_reduction_percent"] for r in results) / n_scenarios, 1
            ),
            "avg_cost_reduction": round(
                sum(r["improvement"]["cost_reduction_percent"] for r in results) / n_scenarios, 1
            ),
        },
    }
    report_path = Path(exchange_root) / "dataset" / "validation_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"\nОтчёт сохранён: {report_path}")
    return report


if __name__ == "__main__":
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:\1c_agent\exchange"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    run_experiments(ex, n)