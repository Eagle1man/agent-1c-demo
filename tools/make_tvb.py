# -*- coding: utf-8 -*-
"""Вариант B: seed-форма + Commands без кнопок. Проверка: дело в кнопках или командах."""
import shutil
from pathlib import Path

SRC = Path(r"C:\1c_bases\epf_seed2")
DST = Path(r"C:\1c_bases\epf_tvb")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
# переименовать корень/каталог/имя
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "SeedData" in t:
            f.write_text(t.replace("SeedData", "TestCmd"), encoding="utf-8")
(DST / "SeedData.xml").rename(DST / "TestCmd.xml")
(DST / "SeedData").rename(DST / "TestCmd")
# добавить Commands в Form.xml (без кнопок)
fp = DST / "TestCmd" / "Forms" / "Форма" / "Ext" / "Form.xml"
t = fp.read_text(encoding="utf-8")
cmds = ("<Commands>"
        '<Command name="ТестКоманда" id="1">'
        "<Title><v8:item><v8:lang>ru</v8:lang><v8:content>Тест</v8:content></v8:item></Title>"
        "<Action>ПриОткрытии</Action>"
        "</Command>"
        "</Commands>")
assert "</Form>" in t
t = t.replace("</Form>", cmds + "</Form>")
fp.write_text(t, encoding="utf-8")
print("tvb ready")
