# -*- coding: utf-8 -*-
"""Реестр навыков с версиями и управляемыми статусами (ТЗ §20).

Ключевое правило: успешный тест **не** даёт агенту права активировать навык.
Переходы делает человек или явно уполномоченный процесс; автоматического
`draft → active` в модели нет.

Статусы (ТЗ §20): hypothesis → draft_solution → verified_candidate →
approved → active → deprecated. Разрешённые переходы заданы таблицей
`ALLOWED_TRANSITIONS`; попытка шагнуть иначе отклоняется.

API соответствует `tests/test_permissions.py`.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class SkillStatus(Enum):
    HYPOTHESIS = "hypothesis"
    DRAFT_SOLUTION = "draft_solution"
    VERIFIED_CANDIDATE = "verified_candidate"
    APPROVED = "approved"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


ALLOWED_TRANSITIONS = {
    SkillStatus.HYPOTHESIS: {SkillStatus.DRAFT_SOLUTION, SkillStatus.DEPRECATED},
    SkillStatus.DRAFT_SOLUTION: {SkillStatus.VERIFIED_CANDIDATE, SkillStatus.DEPRECATED},
    SkillStatus.VERIFIED_CANDIDATE: {SkillStatus.APPROVED, SkillStatus.DEPRECATED},
    SkillStatus.APPROVED: {SkillStatus.ACTIVE, SkillStatus.DEPRECATED},
    SkillStatus.ACTIVE: {SkillStatus.DEPRECATED},
    SkillStatus.DEPRECATED: set(),
}


class Skill:
    """Навык: версионируемая процедура с условиями, ограничениями и тестами."""

    def __init__(
        self,
        *,
        skill_id: str,
        name: str,
        purpose: str,
        scope: str,
        instructions: str,
        limitations: Optional[list] = None,
        version: str = "0.1.0",
        status: SkillStatus = SkillStatus.HYPOTHESIS,
        test_report: Optional[str] = None,
        test_passed: Optional[bool] = None,
        approved_by: Optional[str] = None,
        approval_date: Optional[str] = None,
        history: Optional[list] = None,
        created_ts: Optional[str] = None,
    ):
        self.skill_id = skill_id
        self.name = name
        self.purpose = purpose
        self.scope = scope
        self.instructions = instructions
        self.limitations = list(limitations or [])
        self.version = version
        self.status = status
        self.test_report = test_report
        self.test_passed = test_passed
        self.approved_by = approved_by
        self.approval_date = approval_date
        self.history = list(history or [])
        self.created_ts = created_ts or now_ts()

    def add_history(self, action: str, note: str) -> None:
        self.history.append({"ts": now_ts(), "action": action, "note": note})

    def to_dict(self) -> dict:
        return {
            "skill_id": self.skill_id,
            "name": self.name,
            "purpose": self.purpose,
            "scope": self.scope,
            "instructions": self.instructions,
            "limitations": self.limitations,
            "version": self.version,
            "status": self.status.value,
            "test_report": self.test_report,
            "test_passed": self.test_passed,
            "approved_by": self.approved_by,
            "approval_date": self.approval_date,
            "history": self.history,
            "created_ts": self.created_ts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Skill":
        try:
            status = SkillStatus(data.get("status", "hypothesis"))
        except ValueError:
            status = SkillStatus.HYPOTHESIS
        return cls(
            skill_id=data.get("skill_id") or str(uuid.uuid4()),
            name=data.get("name", ""),
            purpose=data.get("purpose", ""),
            scope=data.get("scope", ""),
            instructions=data.get("instructions", ""),
            limitations=data.get("limitations", []),
            version=data.get("version", "0.1.0"),
            status=status,
            test_report=data.get("test_report"),
            test_passed=data.get("test_passed"),
            approved_by=data.get("approved_by"),
            approval_date=data.get("approval_date"),
            history=data.get("history", []),
            created_ts=data.get("created_ts"),
        )


class SkillCatalog:
    """JSON-реестр навыков рядом с exchange-каталогом."""

    def __init__(self, exchange_root: str):
        self.root = Path(exchange_root)
        self.catalog_path = self.root / "skills.json"
        self._skills: dict[str, Skill] = {}
        self.load_all()

    # ------------------------------------------------------------ хранилище
    def load_all(self) -> None:
        self._skills = {}
        if not self.catalog_path.exists():
            return
        try:
            data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        for item in data.get("skills", []):
            try:
                skill = Skill.from_dict(item)
            except (TypeError, ValueError):
                continue
            self._skills[skill.skill_id] = skill

    def save_all(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            tmp = self.catalog_path.with_suffix(".json.tmp")
            payload = {"skills": [s.to_dict() for s in self._skills.values()]}
            with tmp.open("w", encoding="utf-8", newline="\n") as fh:
                json.dump(payload, fh, ensure_ascii=False, indent=2)
            os.replace(tmp, self.catalog_path)
            return True
        except OSError as exc:
            print(f"[skills_catalog] сбой записи: {exc}")
            return False

    # ------------------------------------------------------------ создание
    def _new(
        self,
        skill_id: str,
        name: str,
        purpose: str,
        scope: str,
        instructions: str,
        limitations: Optional[list],
        version: str,
        status: SkillStatus,
        **extra,
    ) -> Skill:
        skill = Skill(
            skill_id=skill_id,
            name=name,
            purpose=purpose,
            scope=scope,
            instructions=instructions,
            limitations=limitations,
            version=version,
            status=status,
            **extra,
        )
        skill.add_history("created", f"навык создан в статусе {status.value}")
        self._skills[skill.skill_id] = skill
        self.save_all()
        return skill

    def create_draft(self, *, skill_id: str, name: str, purpose: str, scope: str,
                     instructions: str, limitations: Optional[list] = None,
                     version: str = "0.1.0") -> Skill:
        return self._new(skill_id, name, purpose, scope, instructions,
                         limitations, version, SkillStatus.HYPOTHESIS)

    def create_verified_candidate(self, *, skill_id: str, name: str, purpose: str,
                                  scope: str, instructions: str,
                                  limitations: Optional[list] = None,
                                  version: str = "0.1.0",
                                  test_report: str = "",
                                  test_passed: bool = False) -> Skill:
        status = SkillStatus.VERIFIED_CANDIDATE if test_passed else SkillStatus.HYPOTHESIS
        skill = self._new(skill_id, name, purpose, scope, instructions,
                          limitations, version, status,
                          test_report=test_report, test_passed=test_passed)
        skill.add_history(
            "tests_attached",
            f"отчёт: {test_report or 'нет'}, пройдены: {test_passed}",
        )
        self.save_all()
        return skill

    def create_approved(self, *, skill_id: str, name: str, purpose: str, scope: str,
                        instructions: str, limitations: Optional[list] = None,
                        version: str = "1.0.0", approved_by: str = "",
                        approval_date: str = "") -> Skill:
        if not approved_by:
            raise ValueError("approved_by обязателен: навык не утверждается анонимно")
        # Создаём кандидата и утверждаем штатным переходом, чтобы обойти
        # контроль статусов было нельзя даже через вспомогательный метод.
        skill = self._new(skill_id, name, purpose, scope, instructions,
                          limitations, version, SkillStatus.VERIFIED_CANDIDATE,
                          test_passed=True)
        skill.approval_date = approval_date or now_ts()
        if self.approve(skill_id, approved_by) is not True:
            raise ValueError(f"утверждение отклонено политикой для '{approved_by}'")
        return self._skills[skill_id]

    # ------------------------------------------------------------ доступ
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self._skills.get(skill_id)

    def list_skills(self, status: Optional[str] = None, scope: Optional[str] = None) -> list:
        st = status.value if isinstance(status, SkillStatus) else status
        result = []
        for skill in self._skills.values():
            if st is not None and skill.status.value != st:
                continue
            if scope is not None and skill.scope != scope:
                continue
            result.append(skill)
        return result

    # ------------------------------------------------------------ переходы
    def _transition(self, skill_id: str, target: SkillStatus,
                    reason: str = "") -> bool:
        skill = self._skills.get(skill_id)
        if skill is None:
            return False
        if target not in ALLOWED_TRANSITIONS.get(skill.status, set()):
            skill.add_history(
                "transition_refused",
                f"{skill.status.value} → {target.value}: переход не разрешён ({reason or 'без причины'})",
            )
            self.save_all()
            return False
        old = skill.status
        skill.status = target
        skill.add_history("status_changed", f"{old.value} → {target.value}: {reason}")
        self.save_all()
        return True

    def approve(self, skill_id: str, approved_by: str) -> bool:
        """Утвердить навык. Агент или автоматика утвердить не могут."""
        skill = self._skills.get(skill_id)
        if skill is None:
            return False
        if skill.status != SkillStatus.VERIFIED_CANDIDATE:
            skill.add_history("approve_refused", f"статус {skill.status.value}, требуется verified_candidate")
            self.save_all()
            return False
        if not approved_by or any(tag in approved_by.lower() for tag in ("auto", "system", "agent")):
            skill.add_history("approve_refused", f"утверждающий '{approved_by}' не является человеком")
            self.save_all()
            return "requires_manual_review"
        skill.approved_by = approved_by
        skill.approval_date = now_ts()
        return self._transition(skill_id, SkillStatus.APPROVED, f"утвердил {approved_by}")

    def request_review(self, skill_id: str, reason: str = "") -> bool:
        """Запросить рассмотрение. Сам по себе тестов не заменяет."""
        skill = self._skills.get(skill_id)
        if skill is None:
            return False
        skill.add_history("review_requested", reason or "запрошено рассмотрение")
        self.save_all()
        return True

    def activate(self, skill_id: str, reason: str = "") -> object:
        skill = self._skills.get(skill_id)
        if skill is None:
            return False
        if skill.status != SkillStatus.APPROVED:
            skill.add_history("activate_refused", f"статус {skill.status.value}: requires_approval")
            self.save_all()
            return "requires_approval"
        return self._transition(skill_id, SkillStatus.ACTIVE, reason)

    def deprecate(self, skill_id: str, reason: str = "") -> bool:
        return self._transition(skill_id, SkillStatus.DEPRECATED, reason)

    def modify_active_instructions(self, skill_id: str, new_instructions: str) -> bool:
        """Правка инструкций работающего навыка запрещена.

        Изменение оформляется новой версией навыка и проходит статусы заново.
        """
        skill = self._skills.get(skill_id)
        if skill is None:
            return False
        skill.add_history(
            "modify_refused",
            "попытка изменить инструкции активного навыка; требуется новая версия",
        )
        self.save_all()
        return False
