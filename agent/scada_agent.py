# -*- coding: utf-8 -*-
"""
SCADA-агент для системы АгентМост 2.0.
Отвечает за мониторинг датчиков, аварии и команды управления оборудованием.
Наследуется от BaseAgent, работает через exchange/ и SCADA-мост.
"""

import json
import time
import threading
from datetime import datetime
from pathlib import Path

from base_agent import BaseAgent
from scada_bridge import ScadaBridge


def now_ts() -> str:
    return datetime.now().isoformat(timespec="seconds")


class ScadaAgent(BaseAgent):
    """Агент SCADA: мониторинг датчиков, аварии, команды управления."""

    def __init__(self, exchange_root: str,
                 config_path: str = "scada_config.json",
                 poll_interval: float = 2.0):
        super().__init__("scada", exchange_root,
                         profile="оператор_технолог",
                         poll_interval=poll_interval)

        cfg_path = Path(config_path)
        if not cfg_path.is_absolute():
            cfg_path = Path(__file__).resolve().parent / cfg_path

        self.bridge = ScadaBridge(cfg_path, self.root)
        self._last_sensor_read = 0.0
        self._sensor_cache = []

    # ----------------------------- основной цикл -----------------------------
    def _tick(self):
        now = time.time()

        # 1. Читаем датчики с интервалом poll_interval
        if now - self._last_sensor_read >= self.poll_interval:
            self._read_and_publish_sensors()
            self._last_sensor_read = now

        # 2. Проверяем аварии
        self._check_alarms()

        # 3. Обрабатываем входящие задачи (команды управления)
        self._handle_tasks()

    def _read_and_publish_sensors(self):
        try:
            sensors = self.bridge.read_sensors()
            self._sensor_cache = sensors

            self.publish("склад.датчики", {
                "ts": now_ts(),
                "sensors": sensors,
                "source": "scada_agent",
            })

            for s in sensors:
                if s.get("alarm"):
                    self._journal("датчик_тревога", "high", "auto", "тревога",
                                  f"{s['name']}: {s['alarm']} (значение {s['value']} {s['unit']})")
                else:
                    self._journal("датчик_чтение", "low", "auto", "ok",
                                  f"{s['name']}: {s['value']} {s['unit']}")
        except Exception as exc:
            self._journal("склада_ошибка", "high", "auto", "error",
                          f"ошибка чтения датчиков: {exc}")

    def _check_alarms(self):
        try:
            alarms = self.bridge.get_alarms()
            if not getattr(alarms, "available", True):
                # Отказ источника нельзя показывать как «аварий нет» (ТЗ §30).
                self._journal("склада_аварии_недоступны", "high", "auto", "unavailable",
                              f"SCADA не отдала список аварий: {alarms.error}")
                return
            for alarm in alarms:
                self.publish("склад.аварии", {
                    "ts": now_ts(),
                    "alarm": alarm,
                    "source": "scada_agent",
                })
                self._journal("склада_авария", "high", "auto", "тревога",
                              f"авария SCADA: {alarm.get('message', alarm)}",
                              alarm.get("id"))
        except Exception as exc:
            self._journal("склада_авария_ошибка", "high", "auto", "error",
                          f"ошибка проверки аварий: {exc}")

    def _handle_tasks(self):
        for path in sorted(self.inbox.glob("*.json")):
            if path.name.endswith(".tmp") or "__processed" in path.name:
                continue

            try:
                task = json.loads(path.read_text(encoding="utf-8-sig"))
            except Exception as exc:
                self._archive(path, "parse_error")
                continue

            to = task.get("to")
            if to and to != self.agent_id:
                continue

            action = task.get("action", "")
            params = task.get("params", {})
            risk = task.get("risk", "high")

            if action == "отправить_команду":
                self._handle_command(task, params, risk, path)
            elif action == "прочитать_датчики":
                self._handle_read_sensors(task, path)
            elif action == "проверка_связи":
                self._handle_ping(task, path)
            else:
                self._archive(path, "unknown_action")

            try:
                path.replace(path.parent / f"{path.stem}__processed.json")
            except Exception:
                pass

    def _handle_command(self, task, params, risk, path):
        # ТЗ §11.1 и §23: категория C (исполнение команд) отключена для ИИ.
        # Агент не должен иметь пути к оборудованию в обход этого решения.
        self._journal("склада_команда_запрет", "high", "policy", "forbidden",
                      f"команда {params.get('tag')}={params.get('value')} отклонена политикой",
                      task.get("id"))
        self._write_response(task, {
            "protocol": "1.0",
            "id": task.get("id"),
            "ts": now_ts(),
            "status": "forbidden",
            "error": {
                "code": "policy_denied",
                "message": ("Отправка команд оборудованию отключена (ТЗ §11.1). "
                            "Нужно отдельное решение с оценкой риска."),
            },
            "executed_by": "scada_agent",
        })
        return

    def _handle_read_sensors(self, task, path):
        sensors = self.bridge.read_sensors()
        self._journal("склада_датчики_запрос", "low", "auto", "ok",
                      f"прочитано датчиков: {len(sensors)}",
                      task.get("id"))

        resp = {
            "protocol": "1.0",
            "id": task.get("id"),
            "ts": now_ts(),
            "status": "ok",
            "result": {"sensors": sensors, "count": len(sensors)},
            "executed_by": "scada_agent",
        }
        self._write_response(task, resp)

    def _handle_ping(self, task, path):
        try:
            if self.sensors:
                tag = self.sensors[0].get("tag", "")
                self.bridge._get(f"/api/data/current?tag={tag}", timeout=5.0)
                status = "ok"
                message = "связь со SCADA есть"
            else:
                status = "ok"
                message = "SCADA-агент работает (без датчиков в конфиге)"
        except Exception:
            status = "error"
            message = "SCADA недоступен"

        self._journal("склада_проверка_связи", "low", "auto", status, message,
                      task.get("id"))

        resp = {
            "protocol": "1.0",
            "id": task.get("id"),
            "ts": now_ts(),
            "status": status,
            "result": {"platform": "RapidSCADA (HTTP API)", "message": message},
            "executed_by": "scada_agent",
        }
        self._write_response(task, resp)

    def _write_response(self, task, resp):
        cid = task.get("id", str(uuid.uuid4()))
        out_path = self.outbox / f"{cid}.json"
        tmp = out_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(resp, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(out_path)

    def get_latest_sensors(self):
        return self._sensor_cache


if __name__ == "__main__":
    import sys
    ex = sys.argv[1] if len(sys.argv) > 1 else r"C:c_agent\exchange"
    a = ScadaAgent(ex)
    try:
        a.start()
        print("SCADA-агент запущен. Работает 15 секунд... (Ctrl+C для остановки)")
        time.sleep(15)
        print("Последние датчики:", json.dumps(a.get_latest_sensors(), ensure_ascii=False, indent=2))
    except KeyboardInterrupt:
        pass
    finally:
        a.stop()
