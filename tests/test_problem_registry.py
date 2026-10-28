# -*- coding: utf-8 -*-
"""Тесты реестра проблем (problem_registry)."""
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))
from problem_registry import ProblemRegistry, Problem, ProblemCategory, ProblemStatus

FAILED = []
PASSED = 0


def check(name, cond, detail=""):
    global PASSED
    if cond:
        PASSED += 1
        print(f"  [PASS] {name}")
    else:
        FAILED.append(name)
        print(f"  [FAIL] {name} {detail}")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="problem_registry_test_"))
    try:
        registry = ProblemRegistry(str(tmp))

        # 1. Создание проблемы
        prob = registry.create_problem(
            category=ProblemCategory.ERROR_MODEL,
            description="Модель даёт неверный остаток товара",
            evidence=["event_123", "event_456"],
            related_events=["event_123", "event_456"],
        )
        check("проблема создана с UUID", len(prob.problem_id) > 0)
        check("категория установлена", prob.category == ProblemCategory.ERROR_MODEL)
        check("статус — hypothesis", prob.status == ProblemStatus.HYPOTHESIS)
        check("occurrence_count начальное", prob.occurrence_count == 2)

        # 2. Получение проблемы по ID
        fetched = registry.get_problem(prob.problem_id)
        check("проблема найдена по ID", fetched is not None)
        check("описание совпадает", fetched.description == "Модель даёт неверный остаток товара")

        # 3. Добавление гипотезы (не причина!)
        registry.add_hypothesis(
            prob.problem_id,
            description="Недостаток товарных остатков в RAG-базе",
            confidence=0.7,
            evidence_ref="event_123",
        )
        fetched = registry.get_problem(prob.problem_id)
        check("гипотеза добавлена", len(fetched.diagnostic_hypotheses) == 1)
        check("гипотеза не является подтверждённой причиной",
              fetched.root_cause_confirmed is False)

        # 4. Подтверждение причины (только после доказательств)
        registry.add_evidence(prob.problem_id, {"source": "audit_log", "data": "found root cause"})
        result = registry.confirm_root_cause(
            prob.problem_id,
            hypothesis_index=0,
            evidence_summary="Аудит показал, что товары не индексированы",
        )
        check("причина подтверждена", result is True)
        fetched = registry.get_problem(prob.problem_id)
        check("root_cause_confirmed=True", fetched.root_cause_confirmed is True)

        # 5. Приоритизация
        registry.set_priority(prob.problem_id, "high")
        fetched = registry.get_problem(prob.problem_id)
        check("приоритет high", fetched.priority == "high")

        # 6. Связь с тестом
        registry.link_test(prob.problem_id, "test_остатки_товара_v1")
        fetched = registry.get_problem(prob.problem_id)
        check("тест связан", "test_остатки_товара_v1" in fetched.related_tests)

        # 7. Все категории проблем
        categories_expected = [
            ProblemCategory.ERROR_SEARCH_KNOWLEDGE,
            ProblemCategory.ERROR_MODEL,
            ProblemCategory.ERROR_INTEGRATION_1C,
            ProblemCategory.BUSINESS_RULE_VIOLATION,
            ProblemCategory.AMBIGUOUS_QUERY,
            ProblemCategory.UNKNOWN,
        ]
        for cat in categories_expected:
            p = registry.create_problem(category=cat, description=f"Test {cat.value}")
            check(f"категория создана: {cat.value}", p.category == cat)

        # 8. Все статусы
        statuses_expected = [
            ProblemStatus.HYPOTHESIS,
            ProblemStatus.DRAFT_SOLUTION,
            ProblemStatus.VERIFIED_CANDIDATE,
            ProblemStatus.APPROVED,
            ProblemStatus.FIXED,
        ]
        for st in statuses_expected:
            p = registry.create_problem(
                category=ProblemCategory.UNKNOWN,
                description=f"Status test {st.value}",
                initial_status=st,
            )
            check(f"статус установлен: {st.value}", p.status == st)

        # 9. Поиск по категории и статусу
        problems = registry.list_problems(category=ProblemCategory.ERROR_MODEL.value)
        check("поиск по категории", len(problems) >= 1)

        approved = registry.list_problems(status=ProblemStatus.APPROVED.value)
        check("поиск по статусу", len(approved) >= 1)

        # 10. Сохранение и загрузка после перезапуска
        registry.save_all()
        registry2 = ProblemRegistry(str(tmp))
        registry2.load_all()
        fetched_after = registry2.get_problem(prob.problem_id)
        check("проблема восстановлена после перезагрузки", fetched_after is not None)
        check("гипотезы восстановлены", len(fetched_after.diagnostic_hypotheses) == 1)
        check("root_cause подтверждён после перезагрузки", fetched_after.root_cause_confirmed is True)

        # 11. mark_occurrences_increment
        inc_count = registry.get_problem(prob.problem_id).occurrence_count
        registry.increment_occurrence(prob.problem_id)
        fetched = registry.get_problem(prob.problem_id)
        check("occurrence_count увеличен", fetched.occurrence_count == inc_count + 1)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nИТОГ: {PASSED} ok, {len(FAILED)} fail")
    if FAILED:
        for name in FAILED:
            print(f"  -> {name}")
        sys.exit(1)
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")


if __name__ == "__main__":
    main()
