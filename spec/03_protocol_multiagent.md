# Протокол обмена мультиагентов v1.1 (расширение PROTOCOL.md)

## Каталоги обмена
```
exchange/
├── chat/
│   ├── requests/      — запрос пользователя из 1С → chat_service.py
│   ├── responses/     — ответ chat_service.py → 1С
│   ├── archive/       — архив запросов/ответов
│   ├── log/           — сервисный лог
│   └── state.json     — состояние диалога (да/нет)
├── agents/
│   ├── inbox/<agent_id>.json      — входящие задачи для агента
│   ├── outbox/<agent_id>.json     — исходящие результаты от агента
│   ├── blackboard/<topic>.json    — общая доска объявлений (координатор пишет, агенты читают)
│   ├── conflicts/<id>.json        — зарегистрированные конфликты (доступ координатору)
│   └── human_confirm/<id>.json    — запросы на подтверждение человека
```

## Формат сообщения агента (JSON)
```json
{
  "protocol": "1.1",
  "id": "<uuid>",
  "ts": "2026-10-22T16:00:00",
  "from": "координатор",
  "to": "кладовщик",
  "topic": "проверить_остаток",
  "action": "запрос_1с",
  "profile": "бухгалтер",
  "risk": "low",
  "params": { "query": "ВЫБРАТЬ ...", "item": "Товар А" },
  "confirmed_by": null,
  "reply_to": "<uuid или null>",
  "ttl_sec": 30
}
```

## Формат результата агента (JSON)
```json
{
  "protocol": "1.1",
  "id": "<uuid ответа>",
  "ts": "...",
  "from": "кладовщик",
  "to": "координатор",
  "in_response_to": "<uuid задачи>",
  "status": "ok | error | need_confirmation",
  "result": { ... },
  "error": { "code": "...", "message": "..." },
  "executed_by": "агент_кладовщик 1.1"
}
```

## Жизненный цикл задачи
1. Пользователь или координатор пишет задачу в `agents/inbox/<agent_id>.json` (или в `agents/blackboard/<topic>.json`).
2. Агент читает задачу, выполняет её через `chat_service.py` (шлюз к 1С).
3. Агент пишет результат в `agents/outbox/<agent_id>.json`.
4. Координатор собирает результаты, принимает решение: следующая задача, конфликт, ошибка или завершение.
5. При `risk=high` координатор запрашивает подтверждение человека через `agents/human_confirm/<id>.json` и форму 1С.
6. Все действия фиксируются в `exchange/chat/log/service.log` и `journal.jsonl`.

## Состояния (state.json)
- `idle` — простой.
- `processing` — задача в работе.
- `awaiting_human` — ждёт подтверждения человека.
- `conflict` — обнаружен конфликт целей агентов.
- `error` — сбой одного из агентов.