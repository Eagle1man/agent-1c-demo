import re
from pathlib import Path

text = (Path(r"D:\agent-1c-demo") / "1c" / "АгентМост.bsl").read_text(encoding="utf-8-sig")
declared = set(m.group(1) for m in re.finditer(
    r"^\s*(?:Процедура|Функция)\s+([A-Za-zА-Яа-я_0-9]+)", text, re.M))

calls = {}
for m in re.finditer(r"([A-Za-zА-Яа-я_0-9]+)\s*\(", text):
    name = m.group(1)
    if not re.search(r"[А-Яа-я]", name):
        continue
    line = text[:m.start()].count("\n") + 1
    calls.setdefault(name, []).append(line)

known = set("""
Если ИначеЕсли Для Каждого Из Цикл Пока Возврат Новый НЕ И ИЛИ Тогда Иначе КонецЕсли
КонецЦикла Попытка Исключение КонецПопытки
Строка Число Дата Булево ТипЗнч Тип Метаданные Документы Справочники РегистрыСведений
Найти Сред Лев Прав СокрЛП СтрДлина СтрЗаменить СтрНайти СтрРазделить СтрСоединить
Формат ТекущаяДата ТекущаяУниверсальнаяДата ВРег НРег ТРег Символ Символы
ОписаниеОшибки ИнформацияОбОшибке ВызватьИсключение
ОткрытьФорму Предупреждение ПоказатьВопрос Вопрос ПоказатьОповещениеПользователя
НачатьАсинхронныйВызов
""".split())

missing = {n: ls for n, ls in calls.items() if n not in declared and n not in known}
print("вызовы без объявления (проверить вручную):")
for n, ls in sorted(missing.items(), key=lambda kv: kv[1][0]):
    print(f"  {n:32} строки {ls[:6]}")
print("всего:", len(missing))
