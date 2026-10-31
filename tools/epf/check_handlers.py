import re
from pathlib import Path

root = Path(r"D:\agent-1c-demo")
form_xml = (root / "build" / "epf_src" / "АгентМост" / "Forms" / "Форма" / "Ext" / "Form.xml").read_text(encoding="utf-8-sig")
bsl = (root / "1c" / "АгентМост.bsl").read_text(encoding="utf-8-sig")

handlers = sorted(set(re.findall(r"<Handler>([^<]+)</Handler>", form_xml)))
print("обработчиков в форме:", len(handlers))
declared = set(re.findall(r"^(?:Процедура|Функция)\s+([A-Za-zА-Яа-я_0-9]+)", bsl, re.M))
missing = [h for h in handlers if h not in declared]
for h in handlers:
    print(("  OK   " if h in declared else "  НЕТ  ") + h)
if missing:
    print("\nОТСУТСТВУЮТ В МОДУЛЕ:", ", ".join(missing))
else:
    print("\nвсе обработчики формы объявлены в модуле")
