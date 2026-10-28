# -*- coding: utf-8 -*-
"""Вариант tvfull: форма как у моста (поле+команды+кнопки), модуль заведомо рабочий (seed)."""
import shutil
from pathlib import Path

SRC = Path(r"C:\1c_bases\epf_tvb")
DST = Path(r"C:\1c_bases\epf_tvfull")
if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(SRC, DST)
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "TestCmd" in t:
            f.write_text(t.replace("TestCmd", "TestFull"), encoding="utf-8")
(DST / "TestCmd.xml").rename(DST / "TestFull.xml")
(DST / "TestCmd").rename(DST / "TestFull")

fp = DST / "TestFull" / "Forms" / "Форма" / "Ext" / "Form.xml"
t = fp.read_text(encoding="utf-8")
# атрибут + команды + кнопки
t = t.replace("</Attributes>", """<Attribute name="ПутьКExchange" id="2"><Type><v8:Type>xs:string</v8:Type><v8:StringQualifiers><v8:Length>255</v8:Length><v8:AllowedLength>Variable</v8:AllowedLength></v8:StringQualifiers></Type></Attribute></Attributes>""")
t = t.replace("</Form>", """<Commands><Command name="ЗапуститьМост" id="1"><Title><v8:item><v8:lang>ru</v8:lang><v8:content>Запустить мост</v8:content></v8:item></Title><Action>ПриОткрытии</Action></Command><Command name="ОстановитьМост" id="2"><Title><v8:item><v8:lang>ru</v8:lang><v8:content>Остановить мост</v8:content></v8:item></Title><Action>ПриОткрытии</Action></Command></Commands><ChildItems><InputField name="ПутьКExchange" id="10"><DataPath>ПутьКExchange</DataPath></InputField><UsualButton name="ЗапуститьМост" id="11"><CommandName>ЗапуститьМост</CommandName><Title><v8:item><v8:lang>ru</v8:lang><v8:content>Запустить мост</v8:content></v8:item></Title></UsualButton><UsualButton name="ОстановитьМост" id="12"><CommandName>ОстановитьМост</CommandName><Title><v8:item><v8:lang>ru</v8:lang><v8:content>Остановить мост</v8:content></v8:item></Title></UsualButton></ChildItems></Form>""")
fp.write_text(t, encoding="utf-8")
print("tvfull ready")
