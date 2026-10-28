# -*- coding: utf-8 -*-
"""
Обновлённый реестр проблем для подсистемы улучшения (Эп. "agent-1c-demo").

Соответствует тестам:
- tests/test_problem_registry.py
- tests/test_event_logger.py (через общую запись событий)

Требования:
- проблемы представляются объектами Problem;
- категории и статусы — Enum с доступом через .value и .name;
- реестр читает/пишет JSONL рядом с queries.jsonl;
- гипотезы не считаются подтверждённой причиной до явного подтверждения;
- history записывается на каждое изменение.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class ProblemCategory(Enum):
    SEARCH_KNOWLEDGE = "search_knowledge"
    MODEL_RESPONSE = "model_response"
    INTEGRATION_1C = "integration_1c"
    BUSINESS_RULE_VIOLATION = "business_rule"
    AMBIGUOUS_QUERY = "ambiguous_query"
    UNKNOWN = "unknown"


class ProblemStatus(Enum):
    HYPOTHESIS = "hypothesis"
    DRAFT_SOLUTION = "draft_solution"
    VERIFIED_CANDIDATE = "verified_candidate"
    APPROVED = "approved"
    FIXED = "fixed"


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Problem:
    """Представление проблемы в памяти.

    Поля, ожидаемые тестом:
    problem_id, category, description, status, related_events,
    occurrence_count, priority, evidence, diagnostic_hypotheses,
    root_cause_confirmed, proposed_actions, related_tests,
    approval_status, fix_status, history
    """

    def __init__(
        self,
        *,
        problem_id: str,
        category: ProblemCategory,
        description: str,
        status: ProblemStatus,
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
    ):
        self.problem_id = problem_id
        self.category = category
        self.description = description
        self.status = status
        self.related_events = list(related_events or [])
        self.occurrence_count = occurrence_count
        self.priority = priority
        self.evidence = list(evidence or [])
        self.diagnostic_hypotheses = list(diagnostic_hypotheses or [])
        self.root_cause_confirmed = root_cause_confirmed
        self.proposed_actions = list(proposed_actions or [])
        self.related_tests = list(related_tests or [])
        self.approval_status = approval_status
        self.fix_status = fix_status
        self._history = list(history or [])

    @property
    def diagnostic_hypotheses(self) -> list:
        return list(self._diagnostic_hypotheses)

    @diagnostic_hypotheses.setter
    def diagnostic_hypotheses(self, value: list) -> None:
        self._diagnostic_hypotheses = list(value)

    def add_history(self, action: str, note: str) -> None:
        self._history.append({"ts": now_ts(), "action": action, "note": note})

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
            "history": self._history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Problem":
        try:
            status = ProblemStatus(data.get("status", "hypothesis"))
        except Exception:
            status = ProblemStatus.HYPOTHESIS
        try:
            category = ProblemCategory(data.get("category", "unknown"))
        except Exception:
            category = ProblemCategory.UNKNOWN
        return cls(
            problem_id=data.get("problem_id", str(uuid.uuid4())),
            category=category,
            description=data.get("description", ""),
            status=status,
            related_events=data.get("related_events", []),
            occurrence_count=int(data.get("occurrence_count", 1)),
            priority=data.get("priority", "medium"),
            evidence=data.get("evidence", []),
            diagnostic_hypotheses=data.get("diagnostic_hypotheses", []),
            root_cause_confirmed=bool(data.get("root_cause_confirmed", False)),
            proposed_actions=data.get("proposed_actions", []),
            related_tests=data.get("related_tests", []),
            approval_status=data.get("approval_status", "pending"),
            fix_status=data.get("fix_status", "open"),
            history=data.get("history", []),

class ProblemRegistry:
    """JSONL-реестр проблем рядом с exchange-папкой."""

    def __init__(self, exchange_root: str):
        self.root = Path(exchange_root)
        self.registry_path = self.root / "problems.jsonl"

    # ---------- вспомогательные -------------------------------
    def _validate_category(self, category: Any) -> None:
        if not isinstance(category, ProblemCategory):
            raise ValueError(
                f"ожидается ProblemCategory, получено: {category!r}"
            )

    def _validate_status(self, status: Any) -> None:
        if not isinstance(status, ProblemStatus):
            raise ValueError(f"ожидается ProblemStatus, получено: {status!r}")

    def _validate_priority(self, priority: str) -> None:
        valid = {"low", "medium", "high", "critical"}
        if priority not in valid:
            raise ValueError(f"недопустимый приоритет '{priority}'. {sorted(valid)}")

    def _read_all(self) -> list:
        if not self.registry_path.exists():
            return []
        try:
            lines = self.registry_path.read_text(encoding="utf-8").splitlines()
            problems = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    problems.append(Problem.from_dict(data))
                except json.JSONDecodeError:
                    continue
            return problems
        except Exception:
            return []

    def _find(self, problem_id: str) -> Optional[Problem]:
        for rec in self._read_all():
            if rec.problem_id == problem_id:
                return rec
        return None

    def _append_record(self, record: Problem) -> None:
        try:
            with self.registry_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(record.to_dict(), ensure_ascii=False) + "
")
        except Exception as exc:
            print(f"[problem_registry] сбой записи: {exc}", file=__import__("sys").stderr)

    def _write_all(self, problems: list) -> bool:
        try:
            with self.registry_path.open("w", encoding="utf-8") as fh:
                for rec in problems:
                    fh.write(json.dumps(rec.to_dict(), ensure_ascii=False) + "
")
            return True
        except Exception as exc:
            print(f"[problem_registry] сбой записи реестра: {exc}", file=__import__("sys").stderr)
            return False
        )


