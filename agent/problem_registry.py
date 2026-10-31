# -*- coding: utf-8 -*-
"""Реестр проблем контура непрерывного улучшения (ТЗ §18).

Правила, заложенные в модель:
- проблема создаётся в статусе `hypothesis` и не считается решённой;
- гипотеза — не причина: `root_cause_confirmed` поднимается только явным
  подтверждением с доказательством;
- каждое изменение оставляет запись в `history`;
- хранилище — JSONL рядом с exchange-каталогом, запись атомарная
  (временный файл + переименование), чтобы сбой не портил реестр.

Модуль заменяет два предыдущих нерабочих варианта
(`problem_registry.py` и `problem_registry_v2.py` были синтаксически битыми).
API соответствует `tests/test_problem_registry.py`.
"""
from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ProblemCategory(Enum):
    """Категории проблем (ТЗ §18). Значения — строки для JSONL."""

    ERROR_SEARCH_KNOWLEDGE = "search_knowledge"
    ERROR_MODEL = "model_response"
    ERROR_INTEGRATION_1C = "integration_1c"
    BUSINESS_RULE_VIOLATION = "business_rule"
    AMBIGUOUS_QUERY = "ambiguous_query"
    UNKNOWN = "unknown"


class ProblemStatus(Enum):
    """Жизненный цикл проблемы (ТЗ §18)."""

    HYPOTHESIS = "hypothesis"
    DRAFT_SOLUTION = "draft_solution"
    VERIFIED_CANDIDATE = "verified_candidate"
    APPROVED = "approved"
    FIXED = "fixed"


PRIORITIES = ("low", "medium", "high", "critical")


class Problem:
    """Проблема в памяти. Сериализуется в dict для JSONL."""

    def __init__(
        self,
        *,
        problem_id: str,
        category: ProblemCategory,
        description: str,
        status: ProblemStatus = ProblemStatus.HYPOTHESIS,
        related_events: Optional[list] = None,
        occurrence_count: int = 1,
        priority: str = "medium",
        evidence: Optional[list] = None,
        diagnostic_hypotheses: Optional[list] = None,
        root_cause_confirmed: bool = False,
        proposed_actions: Optional[list] = None,
        related_tests: Optional[list] = None,
        approval_status: str = "pending",
        fix_status: str = "open",
        history: Optional[list] = None,
        created_ts: Optional[str] = None,
    ):
        self.problem_id = problem_id
        self.category = category
        self.description = description
        self.status = status
        self.related_events = list(related_events or [])
        self.occurrence_count = int(occurrence_count)
        self.priority = priority
        self.evidence = list(evidence or [])
        self.diagnostic_hypotheses = list(diagnostic_hypotheses or [])
        self.root_cause_confirmed = bool(root_cause_confirmed)
        self.proposed_actions = list(proposed_actions or [])
        self.related_tests = list(related_tests or [])
        self.approval_status = approval_status
        self.fix_status = fix_status
        self.created_ts = created_ts or now_ts()
        self.history = list(history or [])

    # ------------------------------------------------------------ служебное
    def add_history(self, action: str, note: str) -> None:
        self.history.append({"ts": now_ts(), "action": action, "note": note})

    def to_dict(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "category": self.category.value,
            "description": self.description,
            "status": self.status.value,
            "related_events": self.related_events,
            "occurrence_count": self.occurrence_count,
            "priority": self.priority,
            "evidence": self.evidence,
            "diagnostic_hypotheses": self.diagnostic_hypotheses,
            "root_cause_confirmed": self.root_cause_confirmed,
            "proposed_actions": self.proposed_actions,
            "related_tests": self.related_tests,
            "approval_status": self.approval_status,
            "fix_status": self.fix_status,
            "history": self.history,
            "created_ts": self.created_ts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Problem":
        try:
            category = ProblemCategory(data.get("category", "unknown"))
        except ValueError:
            category = ProblemCategory.UNKNOWN
        try:
            status = ProblemStatus(data.get("status", "hypothesis"))
        except ValueError:
            status = ProblemStatus.HYPOTHESIS
        return cls(
            problem_id=data.get("problem_id") or str(uuid.uuid4()),
            category=category,
            description=data.get("description", ""),
            status=status,
            related_events=data.get("related_events", []),
            occurrence_count=data.get("occurrence_count", 1),
            priority=data.get("priority", "medium"),
            evidence=data.get("evidence", []),
            diagnostic_hypotheses=data.get("diagnostic_hypotheses", []),
            root_cause_confirmed=data.get("root_cause_confirmed", False),
            proposed_actions=data.get("proposed_actions", []),
            related_tests=data.get("related_tests", []),
            approval_status=data.get("approval_status", "pending"),
            fix_status=data.get("fix_status", "open"),
            history=data.get("history", []),
            created_ts=data.get("created_ts"),
        )


class ProblemRegistry:
    """JSONL-реестр проблем.

    In-memory словарь — источник истины в рамках процесса; файл пишется
    целиком при каждом изменении (объём реестра мал, атомарность важнее).
    """

    def __init__(self, exchange_root: str):
        self.root = Path(exchange_root)
        self.registry_path = self.root / "problems.jsonl"
        self._problems: dict[str, Problem] = {}
        self.load_all()

    # ------------------------------------------------------------ чтение/запись
    def load_all(self) -> None:
        self._problems = {}
        if not self.registry_path.exists():
            return
        try:
            text = self.registry_path.read_text(encoding="utf-8")
        except OSError:
            return
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                prob = Problem.from_dict(json.loads(line))
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            self._problems[prob.problem_id] = prob

    def save_all(self) -> bool:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            tmp = self.registry_path.with_suffix(".jsonl.tmp")
            with tmp.open("w", encoding="utf-8", newline="\n") as fh:
                for prob in self._problems.values():
                    fh.write(json.dumps(prob.to_dict(), ensure_ascii=False) + "\n")
            os.replace(tmp, self.registry_path)
            return True
        except OSError as exc:
            print(f"[problem_registry] сбой записи реестра: {exc}")
            return False

    # ------------------------------------------------------------ проверки
    @staticmethod
    def _validate_category(category: Any) -> None:
        if not isinstance(category, ProblemCategory):
            raise ValueError(f"ожидается ProblemCategory, получено: {category!r}")

    @staticmethod
    def _validate_priority(priority: str) -> None:
        if priority not in PRIORITIES:
            raise ValueError(f"недопустимый приоритет '{priority}'. Допустимые: {', '.join(PRIORITIES)}")

    # ------------------------------------------------------------ создание
    def create_problem(
        self,
        category: ProblemCategory,
        description: str,
        evidence: Optional[list] = None,
        related_events: Optional[list] = None,
        initial_status: Optional[ProblemStatus] = None,
        priority: str = "medium",
    ) -> Problem:
        self._validate_category(category)
        self._validate_priority(priority)
        status = initial_status or ProblemStatus.HYPOTHESIS
        if not isinstance(status, ProblemStatus):
            raise ValueError(f"ожидается ProblemStatus, получено: {status!r}")

        # Частота повторения: сколько событий/доказательств пришло с проблемой.
        count = max(1, len(related_events or []), len(evidence or []))

        prob = Problem(
            problem_id=str(uuid.uuid4()),
            category=category,
            description=description,
            status=status,
            related_events=related_events,
            occurrence_count=count,
            priority=priority,
            evidence=evidence,
        )
        prob.add_history("registered", "проблема зарегистрирована")
        self._problems[prob.problem_id] = prob
        self.save_all()
        return prob

    # ------------------------------------------------------------ доступ
    def get_problem(self, problem_id: str) -> Optional[Problem]:
        return self._problems.get(problem_id)

    def list_problems(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
    ) -> list:
        cat = category.value if isinstance(category, ProblemCategory) else category
        st = status.value if isinstance(status, ProblemStatus) else status
        result = []
        for prob in self._problems.values():
            if cat is not None and prob.category.value != cat:
                continue
            if st is not None and prob.status.value != st:
                continue
            result.append(prob)
        return result

    def get_unapproved(self) -> list:
        return [p for p in self._problems.values() if p.approval_status == "pending"]

    # ------------------------------------------------------------ изменения
    def _mutate(self, problem_id: str) -> Optional[Problem]:
        prob = self._problems.get(problem_id)
        return prob

    def add_hypothesis(
        self,
        problem_id: str,
        description: str,
        confidence: Any = "low",
        evidence_ref: Any = None,
    ) -> bool:
        prob = self._mutate(problem_id)
        if prob is None:
            return False
        prob.diagnostic_hypotheses.append({
            "hypothesis": description,
            "confidence": confidence,
            "evidence_ref": evidence_ref,
            "added_ts": now_ts(),
            "confirmed": False,
        })
        prob.add_history("hypothesis_added", f"добавлена гипотеза (уверенность: {confidence})")
        self.save_all()
        return True

    def add_evidence(self, problem_id: str, evidence_item: dict) -> bool:
        prob = self._mutate(problem_id)
        if prob is None:
            return False
        prob.evidence.append(evidence_item)
        prob.occurrence_count += 1
        prob.add_history("evidence_added", f"добавлено доказательство (всего: {len(prob.evidence)})")
        self.save_all()
        return True

    def confirm_root_cause(
        self,
        problem_id: str,
        hypothesis_index: int,
        evidence_summary: str = "",
    ) -> bool:
        """Подтвердить причину. Без доказательства подтверждение не принимается."""
        prob = self._mutate(problem_id)
        if prob is None:
            return False
        hyps = prob.diagnostic_hypotheses
        if hypothesis_index < 0 or hypothesis_index >= len(hyps):
            return False
        if not evidence_summary and not prob.evidence:
            return False
        hyps[hypothesis_index]["confirmed"] = True
        hyps[hypothesis_index]["confirmed_ts"] = now_ts()
        prob.root_cause_confirmed = True
        prob.add_history(
            "root_cause_confirmed",
            f"гипотеза #{hypothesis_index} подтверждена как причина: {evidence_summary or 'см. evidence'}",
        )
        self.save_all()
        return True

    def set_priority(self, problem_id: str, priority: str) -> bool:
        self._validate_priority(priority)
        prob = self._mutate(problem_id)
        if prob is None:
            return False
        prob.priority = priority
        prob.add_history("priority_changed", f"приоритет: {priority}")
        self.save_all()
        return True

    def link_test(self, problem_id: str, test_name: str) -> bool:
        prob = self._mutate(problem_id)
        if prob is None:
            return False
        if test_name not in prob.related_tests:
            prob.related_tests.append(test_name)
        prob.add_history("test_linked", f"связан тест: {test_name}")
        self.save_all()
        return True

    def set_status(self, problem_id: str, status: ProblemStatus) -> bool:
        if not isinstance(status, ProblemStatus):
            return False
        prob = self._mutate(problem_id)
        if prob is None:
            return False
        old = prob.status
        prob.status = status
        prob.add_history("status_changed", f"{old.value} → {status.value}")
        self.save_all()
        return True

    def set_approval(self, problem_id: str, status: str, approved_by: Optional[str] = None) -> bool:
        if status not in ("pending", "approved", "rejected"):
            return False
        prob = self._mutate(problem_id)
        if prob is None:
            return False
        prob.approval_status = status
        prob.add_history(
            "approval_changed",
            f"утверждение: {status}" + (f" (утвердил: {approved_by})" if approved_by else ""),
        )
        self.save_all()
        return True

    def set_fix_status(self, problem_id: str, status: str) -> bool:
        if status not in ("open", "in_progress", "fixed", "rejected", "deferred"):
            return False
        prob = self._mutate(problem_id)
        if prob is None:
            return False
        prob.fix_status = status
        prob.add_history("fix_status_changed", f"исправление: {status}")
        self.save_all()
        return True

    def increment_occurrence(self, problem_id: str) -> bool:
        prob = self._mutate(problem_id)
        if prob is None:
            return False
        prob.occurrence_count += 1
        prob.add_history("occurrence_incremented", f"повторов: {prob.occurrence_count}")
        self.save_all()
        return True
