# -*- coding: utf-8 -*-
"""
Разрешение конфликтов между агентами мультиагентной системы.

Конфликт возникает, когда цели агентов противоречат:
  - кладовщик говорит "товара нет", логист требует "отгрузить завтра".
  - закупки хотят заказать у поставщика А, бухгалтер blokирует из-за долга.
"""
import json
import uuid
from datetime import datetime
from pathlib import Path


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ConflictResolver:
    def __init__(self, exchange_root: str):
        self.root = Path(exchange_root)
        self.conflicts_dir = self.root / "agents" / "conflicts"
        self.conflicts_dir.mkdir(parents=True, exist_ok=True)

    def register(self, description: str, participants: list,
                 risk: str = "high") -> str:
        cid = str(uuid.uuid4())
        rec = {
            "id": cid,
            "ts": now_ts(),
            "description": description,
            "participants": participants,
            "risk": risk,
            "status": "open",
            "resolution": None,
            "resolved_by": None,
        }
        path = self.conflicts_dir / f"{cid}.json"
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return cid

    def list_open(self):
        return [json.loads(p.read_text(encoding="utf-8-sig"))
                for p in sorted(self.conflicts_dir.glob("*.json"))
                if json.loads(p.read_text(encoding="utf-8-sig")).get("status") == "open"]

    def resolve(self, conflict_id: str, resolution: str,
                resolved_by: str = "координатор") -> bool:
        path = self.conflicts_dir / f"{conflict_id}.json"
        if not path.exists():
            return False
        rec = json.loads(path.read_text(encoding="utf-8-sig"))
        rec["status"] = "разрешено"
        rec["resolution"] = resolution
        rec["resolved_by"] = resolved_by
        rec["resolved_ts"] = now_ts()
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return True

    def escalate_to_human(self, conflict_id: str) -> str:
        """Перенести конфликт на подтверждение человека."""
        rec = json.loads((self.conflicts_dir / f"{conflict_id}.json").read_text(encoding="utf-8-sig"))
        rec["status"] = "эскалировано_человеку"
        rec["escalated_ts"] = now_ts()
        path = self.conflicts_dir / f"{conflict_id}.json"
        path.write_text(json.dumps(rec, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return conflict_id