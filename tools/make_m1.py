# -*- coding: utf-8 -*-
"""Вариант m1: форма моста + минимальный модуль (Перем + пустое ПриОткрытии)."""
import shutil
from pathlib import Path

SRC = Path(r"C:\1c_bases\epf_most")
DST = Path(r"C:\1c_bases\epf_m1")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "АгентМост" in t:
            f.write_text(t.replace("АгентМост", "M1"), encoding="utf-8")
(DST / "АгентМост.xml").rename(DST / "M1.xml")
(DST / "АгентМост").rename(DST / "M1")
mod = DST / "M1" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
mod.write_text("&НаКлиенте\nПерем ПутьКExchange;\n\n&НаКлиенте\nПроцедура ПриОткрытии(Отказ)\n\tПутьКExchange = \"C:\\\\1c_bases\\\\x\";\nКонецПроцедуры\n",
               encoding="utf-8")
print("m1 ready")
