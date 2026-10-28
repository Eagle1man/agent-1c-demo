# Write problem_registry.py - Part 1
# -*- coding: utf-8 -*-
"""
Реестр проблем с уникальными идентификаторами и историей изменений.

Категории проблем:
- search_knowledge — ошибка поиска или отсутствующие знания
- model_response — ошибка ответа модели
- integration_1c — ошибка интеграции с 1С
- business_rule — нарушение бизнес-правил
- ambiguous_query — неоднозначный запрос
- unknown — неизвестная причина

Гипотезы не считаются установленной причиной без достаточных доказательств.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


PROBLEM_CATEGORIES = (
    "search_knowledge",
    "model_response",
    "integration_1c",
    "business_rule",
    "ambiguous_query",
    "unknown",
)

PRIORITIES = ("low", "medium", "high", "critical")
APPROVAL_STATUSES = ("pending", "approved", "rejected")
FIX_STATUSES = ("open", "in_progress", "fixed", "rejected", "deferred")


class ProblemRegistry:
    def __init__(self, exchange_root: str):
        self.root = Path(exchange_root)
        self.registry_path = self.root / "problems.jsonl"

    def _validate_category(self, category: str) -> None:
        if category not in PROBLEM_CATEGORIES:
            raise ValueError(
                f"недопустимая категория '{category}'. "
                f"Допустимые: {', '.join(PROBLEM_CATEGORIES)}"
            )

    def _validate_priority(self, priority: str) -> None:
        if priority not in PRIORITIES:
            raise ValueError(
                f"недопустимый приоритет '{priority}'. "
                f"Допустимые: {', '.join(PRIORITIES)}"
            )

    def register_problem(
        self,
        category: str,
        description: str,
        related_events: Optional[list] = None,
        priority: str = "medium",
        evidence: Optional[list] = None,
        diagnostic_hypotheses: Optional[list] = None,
        proposed_actions: Optional[list] = None,
        related_tests: Optional[list] = None,
    ) -> str:
        self._validate_category(category)
        self._validate_priority(priority)

        problem_id = str(uuid.uuid4())
        rec = {
            "problem_id": problem_id,
            "ts": now_ts(),
            "category": category,
            "description": description,
            "related_events": related_events or [],
            "occurrence_count": 1,
            "priority": priority,
            "evidence": evidence or [],
            "diagnostic_hypotheses": diagnostic_hypotheses or [],
            "root_cause_confirmed": False,
            "proposed_actions": proposed_actions or [],
            "related_tests": related_tests or [],
            "approval_status": "pending",
            "fix_status": "open",
            "history": [
                {
                    "ts": now_ts(),
                    "action": "registered",
                    "note": "проблема зарегистрирована",
                }
            ],
        }
        try:
            with self.registry_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as exc:
            import sys
            print(f"[problem_registry] сбой записи: {exc}", file=sys.stderr)
        return problem_id

    def increment_occurrence(self, problem_id: str) -> bool:
        return self._update_field(problem_id, "occurrence_count", None, increment=True)

    def add_hypothesis(self, problem_id: str, hypothesis: str,
                       evidence_ref: Optional[list] = None,
                       confidence: str = "low") -> bool:
        rec = self._find(problem_id)
        if not rec:
            return False
        hyp = {
            "hypothesis": hypothesis,
            "evidence_ref": evidence_ref or [],
            "confidence": confidence,
            "added_ts": now_ts(),
            "confirmed": False,
        }
        rec["diagnostic_hypotheses"].append(hyp)
        rec["history"].append({
            "ts": now_ts(),
            "action": "hypothesis_added",
            "note": f"добавлена гипотеза (уверенность: {confidence})",
        })
        return self._write_all([rec if r.get("problem_id") == problem_id else r
                                for r in self._read_all()])

    def confirm_root_cause(self, problem_id: str, hypothesis_index: int,
                           evidence_ref: list) -> bool:
        rec = self._find(problem_id)
        if not rec:
            return False
        hyps = rec.get("diagnostic_hypotheses", [])
        if hypothesis_index < 0 or hypothesis_index >= len(hyps):
            return False
        if not evidence_ref:
            return False
        hyps[hypothesis_index]["confirmed"] = True
        hyps[hypothesis_index]["confirmed_ts"] = now_ts()
        rec["root_cause_confirmed"] = True
        rec["history"].append({
            "ts": now_ts(),
            "action": "root_cause_confirmed",
            "note": f"гипотеза #{hypothesis_index} подтверждена как причина",
        })
        return self._write_all([rec if r.get("problem_id") == problem_id else r

    def set_fix_status(self, problem_id: str, status: str) -> bool:
        if status not in FIX_STATUSES:
            return False
        rec = self._find(problem_id)
        if not rec:
            return False
        rec["fix_status"] = status
        rec["history"].append({
            "ts": now_ts(),
            "action": "fix_status_changed",
            "note": f"исправление: {status}",
        })
        return self._write_all([rec if r.get("problem_id") == problem_id else r
                                for r in self._read_all()])

    def add_evidence(self, problem_id: str, evidence_item: dict) -> bool:
        rec = self._find(problem_id)
        if not rec:
            return False
        rec["evidence"].append(evidence_item)
        rec["occurrence_count"] = rec.get("occurrence_count", 1) + 1
        rec["history"].append({
            "ts": now_ts(),
            "action": "evidence_added",
            "note": f"добавлено доказательство (всего: {len(rec['evidence'])})",
        })
        return self._write_all([rec if r.get("problem_id") == problem_id else r
                                for r in self._read_all()])

    def get_problem(self, problem_id: str) -> Optional[dict]:
        return self._find(problem_id)

    def list_problems(self, category: Optional[str] = None,
                      status: Optional[str] = None) -> list:
        problems = self._read_all()
        if category:
            problems = [p for p in problems if p.get("category") == category]
        if status:
            problems = [p for p in problems if p.get("approval_status") == status]
        return problems

    def get_unapproved(self) -> list:
        return [p for p in self._read_all() if p.get("approval_status") == "pending"]

    def _read_all(self) -> list:
        if not self.registry_path.exists():
            return []
        try:
            lines = self.registry_path.read_text(encoding="utf-8").splitlines()
            return [json.loads(l) for l in lines if l.strip()]
        except Exception:
            return []

    def _find(self, problem_id: str) -> Optional[dict]:
        for rec in self._read_all():
            if rec.get("problem_id") == problem_id:
                return rec
        return None

    def _update_field(self, problem_id: str, field: str,
                      value: Any, increment: bool = False) -> bool:
        rec = self._find(problem_id)
        if not rec:
            return False
        if increment:
            rec[field] = rec.get(field, 0) + 1
        elif value is not None:
            rec[field] = value
        rec["history"].append({
            "ts": now_ts(),
            "action": "field_updated",
            "note": f"поле '{field}' обновлено",
        })
        return self._write_all([rec if r.get("problem_id") == problem_id else r
                                for r in self._read_all()])

    def _write_all(self, records: list) -> bool:
        try:
            with self.registry_path.open("w", encoding="utf-8") as fh:
                for rec in records:
                    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
            return True
        except Exception as exc:
            import sys
            print(f"[problem_registry] сбой записи реестра: {exc}", file=sys.stderr)
            return False
                                for r in self._read_all()])

    def set_approval(self, problem_id: str, status: str,
                     approved_by: Optional[str] = None) -> bool:
        if status not in APPROVAL_STATUSES:
            return False
        rec = self._find(problem_id)
        if not rec:
            return False
        rec["approval_status"] = status
        rec["history"].append({
            "ts": now_ts(),
            "action": "approval_changed",
            "note": f"утверждение: {status}" +
                    (f" (утвердил: {approved_by})" if approved_by else ""),
        })
        return self._write_all([rec if r.get("problem_id") == problem_id else r
                                for r in self._read_all()])