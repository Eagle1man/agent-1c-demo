# -*- coding: utf-8 -*-
"""Вариант b3: только Перем + пустое ПриОткрытии (базовый минимум)."""
import shutil
from pathlib import Path

SRC = Path(r"C:\1c_bases\epf_b2")
DST = Path(r"C:\1c_bases\epf_b3")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "B2" in t:
            f.write_text(t.replace("B2", "B3"), encoding="utf-8")
(DST / "B2.xml").rename(DST / "B3.xml")
(DST / "B2").rename(DST / "B3")
mod = DST / "B3" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"
mod.write_text("Перем ПутьКExchange;\n\n&НаКлиенте\nПроцедура ПриОткрытии(Отказ)\nКонецПроцедуры\n",
               encoding="utf-8")
print("b3 ready")
