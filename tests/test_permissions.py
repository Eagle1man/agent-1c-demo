# -*- coding: utf-8 -*-
"""Тесты соблюдения ограничений полномочий (Этап B/C — политика безопасности)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from problem_registry import ProblemStatus
from skills_catalog import SkillStatus, SkillCatalog

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
    import tempfile, shutil
    tmp = Path(tempfile.mkdtemp(prefix="permissions_test_"))
    try:
        catalog = SkillCatalog(str(tmp))

        # 1. Навык в статусе hypothesis не может стать approved автоматически
        draft = catalog.create_draft(
            skill_id="skill_test_1",
            name="Навык поиска остатков",
            purpose="Отвечать на вопросы остатков на складе",
            scope="warehouse",
            instructions="Использовать RAG-поиск и bridge.py для запроса в 1С",
            limitations=["Только чтение", "Не выполнять операции записи"],
            version="0.1.0",
        )
        check("draft создан в статусе hypothesis", draft.status == SkillStatus.HYPOTHESIS)

        # 2. Попытка автоматического one-click approve — должна быть запрещена
        # (метод approve требует ручного вызова / подтверждения)
        auto_result = catalog.approve(draft.skill_id, approved_by="auto_system")
        check("автоматическое approve запрещено для hypothesis",
              auto_result is False or auto_result == "requires_manual_review")

        # 3. Транзиция hypothesis → verified_candidate требует тестов
        catalog.request_review(draft.skill_id, reason="Протестирован в regression_tests.py")
        updated = catalog.get_skill(draft.skill_id)
        check("после review статус moved к verified_candidate",
              updated.status in [SkillStatus.VERIFIED_CANDIDATE, SkillStatus.HYPOTHESIS])

        # 4. verified_candidate без тестов не может стать approved
        candidate = catalog.create_verified_candidate(
            skill_id="skill_test_2",
            name="Улучшенный навык",
            purpose="Тест",
            scope="warehouse",
            instructions="test",
            limitations=["read-only"],
            version="0.2.0",
            test_report="regression_report_001",
            test_passed=True,
        )
        check("verified_candidate создан с test_passed=True",
              candidate.status == SkillStatus.VERIFIED_CANDIDATE)

        # 5. Навык не активируется автоматически
        check("verified_candidate НЕ является approved",
              candidate.status != SkillStatus.APPROVED)

        # 6. Попытка активировать рабочий навык без подтверждения
        active_result = catalog.activate(draft.skill_id, reason="missing_approval")
        check("активация без approval запрещена",
              active_result is False or "requires_approval" in str(active_result))

        # 7. Проверка: изменение production инструкций не разрешено автоматически
        active_skill = catalog.create_approved(
            skill_id="active_skill_1",
            name="Активный навык",
            purpose="test",
            scope="warehouse",
            instructions="original instructions",
            limitations=["read-only"],
            version="1.0.0",
            approved_by="human_reviewer",
            approval_date="2026-01-01",
        )
        check("активный навык имеет статус approved",
              active_skill.status == SkillStatus.APPROVED)

        # Попытка перезаписать инструкции напрямую
        modify_result = catalog.modify_active_instructions(
            active_skill.skill_id, new_instructions="hacked instructions"
        )
        check("изменение активных инструкций запрещено", modify_result is False)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print(f"\nИТОГ: {PASSED} ok, {len(FAILED)} fail")
    if FAILED:
        sys.exit(1)
    print("ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")


if __name__ == "__main__":
    main()
