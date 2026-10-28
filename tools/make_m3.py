# -*- coding: utf-8 -*-
"""Вариант m3: связанное поле + атрибут + минимальный модуль С переменной."""
import shutil
from pathlib import Path

SRC = Path(r"C:\1c_bases\epf_m1")
DST = Path(r"C:\1c_bases\epf_m3")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "M1" in t:
            f.write_text(t.replace("M1", "M3"), encoding="utf-8")
(DST / "M1.xml").rename(DST / "M3.xml")
(DST / "M1").rename(DST / "M3")
fp = DST / "M3" / "Forms" / "Форма" / "Ext" / "Form.xml"
t = fp.read_text(encoding="utf-8")
# атрибут как в TestFull + привязка поля
t = t.replace("</Attributes>",
              '<Attribute name="ПутьКExchange" id="2"><Type><v8:Type>xs:string</v8:Type>'
              "<v8:StringQualifiers><v8:Length>255</v8:Length>"
              "<v8:AllowedLength>Variable</v8:AllowedLength></v8:StringQualifiers>"
              "</Type></Attribute></Attributes>")
t = t.replace('<InputField name="ПутьКExchange" id="10"/>',
              '<InputField name="ПутьКExchange" id="10"><DataPath>ПутьКExchange</DataPath></InputField>')
fp.write_text(t, encoding="utf-8")
print("m3 ready")
