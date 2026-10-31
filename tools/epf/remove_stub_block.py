"""Удаляет из 1c/АгентМост.bsl блок сгенерированных заглушек (строки 736-870).

Причина: в блоке дублируется имя ВыполнитьЗапрос1С, объявление «Процедуру»,
процедуры возвращают значения и вызываются несуществующие методы — модуль
не компилируется. Ни одна из функций блока не используется рабочим кодом
(кроме вызовов внутри самого блока).
"""
from pathlib import Path

path = Path(r"D:\agent-1c-demo") / "1c" / "АгентМост.bsl"
raw = path.read_bytes()
has_bom = raw.startswith(b"\xef\xbb\xbf")
text = raw.decode("utf-8-sig")
lines = text.splitlines()

start, end = 736, 870  # 1-based, включительно
removed = lines[start - 1:end]
assert removed[0].strip() == "&НаКлиенте", f"строка {start}: {removed[0]!r}"
assert removed[-1].strip() == "КонецПроцедуры", f"строка {end}: {removed[-1]!r}"
assert any("Процедуру СоздатьДокумент1С" in l for l in removed), "блок не тот"

kept = lines[:start - 1] + lines[end:]
out = "\r\n".join(kept).rstrip("\r\n") + "\r\n"
data = out.encode("utf-8")
if has_bom:
    data = b"\xef\xbb\xbf" + data
path.write_bytes(data)
print(f"удалено строк: {len(removed)}; осталось: {len(kept)}")
