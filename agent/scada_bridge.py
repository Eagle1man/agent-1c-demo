# -*- coding: utf-8 -*-
"""
Мост к RapidSCADA через HTTP API.
Позволяет читать датчики, получать аварии и отправлять команды управления.
"""

import json
import time
import uuid
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

PROTOCOL = "1.0"


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ScadaBridgeError(Exception):
    pass


class ScadaBridgeTimeout(ScadaBridgeError):
    pass


class AlarmsResult(list):
    """Список аварий с признаком доступности источника.

    ТЗ §30/§40.4: «аварий нет» и «SCADA недоступна» — разные утверждения.
    Объект ведёт себя как список (для существующих вызовов), но несёт
    `available` и `error`, чтобы отказ нельзя было принять за пустой ответ.
    """

    def __init__(self, items=(), *, available: bool = True, error=None):
        super().__init__(items)
        self.available = available
        self.error = error


class ScadaBridge:
    def __init__(self, config_path, exchange_root):
        self.config_path = Path(config_path)
        self.exchange_root = Path(exchange_root)
        self.config = self._load_config()
        self.base_url = self.config.get("scada_url", "http://localhost:5000").rstrip("/")
        self.api_key = self.config.get("api_key", "")
        self.poll_interval = float(self.config.get("poll_interval", 2.0))
        self.sensors = self.config.get("sensors", [])
        self.integration_1c = bool(self.config.get("integration_1c", False))

        self.sensors_dir = self.exchange_root / "sensors"
        self.alarms_dir = self.exchange_root / "alarms"
        self.commands_dir = self.exchange_root / "commands"
        for d in (self.sensors_dir, self.alarms_dir, self.commands_dir):
            d.mkdir(parents=True, exist_ok=True)

    def _load_config(self):
        if self.config_path.exists():
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        return {}

    def _headers(self, extra=None):
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        if extra:
            h.update(extra)
        return h

    def _get(self, path, timeout=10.0):
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url, headers=self._headers(), method="GET")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ScadaBridgeTimeout(f"SCADA недоступен: {exc}")
        except json.JSONDecodeError as exc:
            raise ScadaBridgeError(f"Некорректный JSON от SCADA: {exc}")

    def _post(self, path, data, timeout=10.0):
        url = f"{self.base_url}{path}"
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(url, data=body, headers=self._headers(), method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise ScadaBridgeTimeout(f"SCADA недоступен: {exc}")
        except json.JSONDecodeError as exc:
            raise ScadaBridgeError(f"Некорректный JSON от SCADA: {exc}")

    # ---------------------------------------------------------------- датчики
    def read_sensors(self):
        """Прочитать датчики. Недоступный источник помечается, а не подменяется.

        Раньше здесь генерировались случайные значения при отказе SCADA — это
        выдавало шум за измерения. Теперь значение `None`, статус `unavailable`
        и текст ошибки; вызывающий код обязан это показать.
        """
        results = []
        for sensor in self.sensors:
            tag = sensor.get("tag", "")
            error = None
            try:
                data = self._get(f"/api/data/current?tag={tag}")
                value = data.get("value")
                status = data.get("status", "ok")
            except ScadaBridgeError as exc:
                value = None
                status = "unavailable"
                error = str(exc)

            min_val = sensor.get("min")
            max_val = sensor.get("max")
            alarm = None
            if isinstance(value, (int, float)):
                if min_val is not None and value < min_val:
                    alarm = f"Значение ниже минимума ({min_val})"
                elif max_val is not None and value > max_val:
                    alarm = f"Значение выше максимума ({max_val})"

            result = {
                "id": sensor["id"],
                "name": sensor["name"],
                "value": value,
                "unit": sensor.get("unit", ""),
                "tag": tag,
                "ts": now_ts(),
                "status": status,
                "alarm": alarm,
                "error": error,
            }
            results.append(result)

            if self.integration_1c:
                self._write_sensor_1c(result)

        return results

    def _write_sensor_1c(self, sensor_data):
        path = self.sensors_dir / f"{sensor_data['id']}.json"
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(sensor_data, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(path)

    # ---------------------------------------------------------------- аварии
    def get_alarms(self):
        """Активные аварии. Возвращает AlarmsResult с признаком доступности."""
        try:
            data = self._get("/api/alarms/active")
            alarms = data.get("alarms", [])
            available, error = True, None
        except ScadaBridgeError as exc:
            alarms, available, error = [], False, str(exc)

        if self.integration_1c and alarms:
            for alarm in alarms:
                aid = alarm.get("id", str(uuid.uuid4()))
                path = self.alarms_dir / f"{aid}.json"
                tmp = path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(alarm, ensure_ascii=False, indent=2),
                               encoding="utf-8")
                tmp.replace(path)

        return AlarmsResult(alarms, available=available, error=error)

    # ---------------------------------------------------------------- команды
    def send_command(self, tag, value, command_type="set_value"):
        payload = {
            "tag": tag,
            "value": value,
            "type": command_type,
            "ts": now_ts(),
            "source": "АгентМост SCADA-агент",
        }

        try:
            resp = self._post("/api/command/send", payload)
            if self.integration_1c:
                cmd_id = str(uuid.uuid4())
                path = self.commands_dir / f"{cmd_id}.json"
                cmd_record = {
                    "id": cmd_id,
                    "ts": now_ts(),
                    "tag": tag,
                    "value": value,
                    "type": command_type,
                    "status": resp.get("status", "sent"),
                    "source": "scada_agent",
                }
                tmp = path.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(cmd_record, ensure_ascii=False, indent=2),
                               encoding="utf-8")
                tmp.replace(path)
            return resp
        except ScadaBridgeError as exc:
            return {"status": "error", "error": str(exc)}

    # ---------------------------------------------------------------- журнал
    def log_event(self, action, risk, decision, status, summary, cid=None):
        journal_path = self.exchange_root.parent / "journal.jsonl"
        rec = {
            "ts": now_ts(),
            "id": cid or "-",
            "agent": "scada",
            "action": action,
            "risk": risk,
            "decision": decision,
            "status": status,
            "summary": summary,
        }
        try:
            with journal_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception:
            pass