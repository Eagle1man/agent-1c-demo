# СЖАТЫЙ КОНТЕКСТ ДЛЯ ПЕРЕДАЧИ МОДЕЛИ

## Проект
`D:\agent-1c-demo` — демо ИИ-агента для 1С (учебная 8.3.27.1508). Протокол v1.0: файловый обмен `exchange/commands|responses|archive|log`. Агент работает в 1С, человек подтверждает риск.

## Среда
- База: `C:\1c_bases\DemoAgentT` (копия DemoAgent, живая для тестов)
- Мост: `C:\1c_bases\AgentMost.epf`, путь exchange: `C:\1c_agent\exchange`
- 1С: `C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe`
- Python: `py` (3.14, есть ollama SDK, pywinauto)
- Ollama: `http://127.0.0.1:11434`, модель `qwen2.5:1.5b` (qwen3:4b битая)

## Что работает (проверено)
1. Мост собирается, открывается без ошибок, опрашивает exchange каждые 2 сек
2. Все 3 действия: проверка_связи, запрос_1с (только ВЫБРАТЬ+ПЕРВЫЕ 50), создать_документ (need_confirmation → confirmed_by)
3. Данные: 12 контрагентов, 20 позиций, 385 документов за 2 года (10.2024–09.2026)
4. Веб-интерфейс `agent/web_app.py` на порту 8001 (живая 1С) и 8000 (эмулятор exe)
5. Qwen классифицирует свободные фразы → запросы в 1С
6. `verify_1c.py` — приёмка пройдена; `test_demo.py` — 43 ok

## Ключевые файлы
- `1c/АгентМост.bsl` — исходник (директивы &НаКлиенте добавлены, фиксы: УдалитьФайлы, плейсхолдер Null→null, реквизит ПутьКExchange)
- `1c/ИНСТРУКЦИЯ_1С.md` — инструкция
- `tools/gen_epf_most.py` — генератор EPF (uuid, атрибуты, диалог-код)
- `tools/gen_epf_seed2.py` — генератор данных (385 док)
- `agent/web_app.py` — веб-UI (Qwen, карточки, подтверждение)
- `agent/agent.py`, `agent/bridge.py`, `agent/tools.py`, `agent/mock_bridge.py`
- `verify_1c.py` — приёмка
- `Служебная_записка_ректору.docx`, `Презентация_ректору_ИИ-агенты_v8.pptx`, `схемы/*.png`

## Команды
```bash
# Сборка моста
py tools/gen_epf_most.py
& 'C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe' DESIGNER /F C:\1c_bases\DemoAgentT /LoadExternalDataProcessorOrReportFromFiles C:\1c_bases\epf_most\АгентМост.xml C:\1c_bases\AgentMost.epf /Out C:\1c_bases\epf.log /DisableStartupDialogs

# Запуск 1С с мостом
& 'C:\Program Files (x86)\1cv8t\8.3.27.1508\bin\1cv8t.exe' ENTERPRISE /F C:\1c_bases\DemoAgentT /Execute C:\1c_bases\AgentMost.epf /DisableStartupDialogs
# (кликнуть "Да" на предупреждении безопасности)

# Веб-интерфейс
py agent/web_app.py --no-mock --exchange C:\1c_agent\exchange --port 8001

# Приёмка
py verify_1c.py
py agent/test_demo.py
```

## Известные проблемы
1. Кнопки команд в XML не отрисовываются платформой (квирк) — мост стартует сам при открытии
2. Диалог в 1С: поле «Фраза» + сторожевой таймер (4 сек тишины → ответ). Код в gen_epf_most.py, но НЕ ПРОВЕРЕН в живой 1С (последняя правка не протестирована)
3. Регистры остатков/бухгалтерии отсутствуют в учебной базе — кнопки переведены на продажи/документы
4. qwen3:4b битая (не докачана) — используется qwen2.5:1.5b
5. Порт 8000 занят exe-эмулятором (dist/demo_agent_1c.exe)

## Последнее состояние
- Мост запущен (pid может быть мёртв, перезапускать командой выше)
- Веб на 8001 запущен
- Данные в базе актуальны (385 док)
- Последняя правка: диалог-код в gen_epf_most.py (ПонятьФразу, ОтветитьНаФразу, ПроверитьФразуДиалога) — требует пересборки и теста

## Следующие шаги
1. Пересобрать AgentMost.epf с диалог-кодом
2. Запустить 1С, проверить поле «Фраза»: «проверь связь», «контрагенты», «создай накладную на ООО Лютик 5 шт по 200»
3. Если диалог работает — убрать веб-интерфейс из сценария, оставить только окно 1С
4. Если не работает — откатить диалог-код, оставить веб как основной UI

## Протокол v1.0 (кратко)
- Команда: {protocol, id, ts, action, profile, risk, params, confirmed_by}
- Ответ: {protocol, id, ts, status(ok|error|need_confirmation), result, error, executed_by}
- Коды: invalid_query, unsupported_action, unsupported_doc_type, parse_error, execution_error, io_error
- Запрещено: COM, HTTP, фоновые задания, ЗапуститьПриложение
- Подтверждение: confirmed_by == null → need_confirmation, документ НЕ создаётся
