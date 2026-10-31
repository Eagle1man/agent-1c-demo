"""Правки модуля перед сборкой epf.

1. Убирает объявления `Перем ПутьКExchange` — этот реквизит уже объявлен в
   форме, повторное объявление даёт «Переменная с указанным именем уже
   определена» и модуль не компилируется.
2. Исправляет ПриОткрытии: раньше путь затирался значением по умолчанию
   ДО чтения поля, то есть введённый человеком путь терялся.
"""
from pathlib import Path

path = Path(r"D:\agent-1c-demo") / "1c" / "АгентМост.bsl"
raw = path.read_bytes()
has_bom = raw.startswith(b"\xef\xbb\xbf")
text = raw.decode("utf-8-sig")

before = text

text = text.replace("Перем ПутьКExchange Экспорт;\r\n\r\n", "", 1)
text = text.replace("&НаКлиенте\r\nПерем ПутьКExchange;\r\n", "", 1)

old_body = (
    '\t// ★ единственное место значения по умолчанию; поле формы важнее\r\n'
    '\t\tПутьКExchange = "C:\\1c_agent\\exchange";\r\n'
    "\t\tПопытка\r\n"
    "\t\t\tЗначПоля = ПутьКExchange;\r\n"
    "\t\t\tЕсли ЗначПоля <> Неопределено И СокрЛП(Строка(ЗначПоля)) <> \"\" Тогда\r\n"
    "\t\t\t\tПутьКExchange = СокрЛП(Строка(ЗначПоля));\r\n"
    "\t\t\tКонецЕсли;\r\n"
    "\t\tИсключение\r\n"
    "\t\tКонецПопытки;\r\n"
)
new_body = (
    '\t// ★ единственное место значения по умолчанию; поле формы важнее\r\n'
    '\t\tПопытка\r\n'
    '\t\t\tЕсли СокрЛП(Строка(ПутьКExchange)) = "" Тогда\r\n'
    '\t\t\t\tПутьКExchange = "D:\\agent-1c-demo\\exchange";\r\n'
    "\t\t\tКонецЕсли;\r\n"
    "\t\tИсключение\r\n"
    "\t\tКонецПопытки;\r\n"
)
if old_body not in text:
    raise SystemExit("не найден блок ПриОткрытии — правка не применена")
text = text.replace(old_body, new_body, 1)

if text == before:
    raise SystemExit("ничего не изменилось")

data = text.encode("utf-8")
if has_bom:
    data = b"\xef\xbb\xbf" + data
path.write_bytes(data)
print("модуль исправлен")
print("Перем ПутьКExchange осталось:", text.count("Перем ПутьКExchange"))
