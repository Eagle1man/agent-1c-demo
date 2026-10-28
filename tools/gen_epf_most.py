# -*- coding: utf-8 -*-
"""Генерация XML-исходников АгентМост из 1c/АгентМост.bsl (v2, по эталону дампа).
.bsl НЕ меняется: читается побайтово, директивы &НаКлиенте добавляются
ТОЛЬКО в артефакт сборки (без них обработчики форм молча не выполняются —
доказано на seed: маркер появился только после директив).
Владельцу 1c/АгентМост.bsl: добавить &НаКлиенте перед каждой процедурой/функцией
модуля формы + verify_1c.py проверять их наличие."""
import re
import uuid as _uuid
from pathlib import Path

PROJ = Path(r"C:\Users\diorl\.cline\data\workspaces\chat\agent-1c-demo")
ROOT = Path(r"C:\1c_bases\epf_most")
DECL = '<?xml version="1.0" encoding="utf-8"?>\n'
NS = ('<MetaDataObject xmlns="http://v8.1c.ru/8.3/MDClasses" '
      'xmlns:app="http://v8.1c.ru/8.2/managed-application/core" '
      'xmlns:cfg="http://v8.1c.ru/8.1/data/enterprise/current-config" '
      'xmlns:cmi="http://v8.1c.ru/8.2/managed-application/cmi" '
      'xmlns:ent="http://v8.1c.ru/8.1/data/enterprise" '
      'xmlns:lf="http://v8.1c.ru/8.2/managed-application/logform" '
      'xmlns:style="http://v8.1c.ru/8.1/data/ui/style" '
      'xmlns:sys="http://v8.1c.ru/8.1/data/ui/fonts/system" '
      'xmlns:v8="http://v8.1c.ru/8.1/data/core" '
      'xmlns:v8ui="http://v8.1c.ru/8.1/data/ui" '
      'xmlns:web="http://v8.1c.ru/8.1/data/ui/colors/web" '
      'xmlns:win="http://v8.1c.ru/8.1/data/ui/colors/windows" '
      'xmlns:xen="http://v8.1c.ru/8.3/xcf/enums" '
      'xmlns:xpr="http://v8.1c.ru/8.3/xcf/predef" '
      'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
      'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
      'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.20">')
LFNS = ('<Form xmlns="http://v8.1c.ru/8.3/xcf/logform" '
        'xmlns:app="http://v8.1c.ru/8.2/managed-application/core" '
        'xmlns:cfg="http://v8.1c.ru/8.1/data/enterprise/current-config" '
        'xmlns:dcscor="http://v8.1c.ru/8.1/data-composition-system/core" '
        'xmlns:dcssch="http://v8.1c.ru/8.1/data-composition-system/schema" '
        'xmlns:dcsset="http://v8.1c.ru/8.1/data-composition-system/settings" '
        'xmlns:ent="http://v8.1c.ru/8.1/data/enterprise" '
        'xmlns:lf="http://v8.1c.ru/8.2/managed-application/logform" '
        'xmlns:style="http://v8.1c.ru/8.1/data/ui/style" '
        'xmlns:sys="http://v8.1c.ru/8.1/data/ui/fonts/system" '
        'xmlns:v8="http://v8.1c.ru/8.1/data/core" '
        'xmlns:v8ui="http://v8.1c.ru/8.1/data/ui" '
        'xmlns:web="http://v8.1c.ru/8.1/data/ui/colors/web" '
        'xmlns:win="http://v8.1c.ru/8.1/data/ui/colors/windows" '
        'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
        'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.20">')

EPF_UUID = "4b9b2a01-7c4e-4b1d-9f2a-00000000e101"
FORM_UUID = "4b9b2a01-7c4e-4b1d-9f2a-00000000e102"
OBJ_UUID = "4b9b2a01-7c4e-4b1d-9f2a-00000000e103"
TYPE_UUID = "4b9b2a01-7c4e-4b1d-9f2a-00000000e104"
VALUE_UUID = "4b9b2a01-7c4e-4b1d-9f2a-00000000e105"
NAME = "АгентМост"

bsl = (PROJ / "1c" / "АгентМост.bsl").read_bytes().decode("utf-8-sig")
i_obj = bsl.index("// === МОДУЛЬ ОБЪЕКТА ===")
i_form = bsl.index("// === МОДУЛЬ ФОРМЫ ===")
obj_code = bsl[i_obj:i_form].strip() + "\n"
form_code = bsl[i_form:].strip() + "\n"
assert "ПодключитьОбработчикОжидания" in form_code


def add_client(code):
    # Идемпотентно: в исходнике директивы уже есть (M1-паттерн), дубли не плодим.
    out = []
    prev_sig = ""
    for line in code.splitlines(keepends=True):
        if line.startswith(("Процедура ", "Функция ")):
            if not prev_sig.startswith("&"):
                out.append("&НаКлиенте\n")
        out.append(line)
        if line.strip() and not line.strip().startswith("//"):
            prev_sig = line.strip()
    return "".join(out)


form_code_out = add_client(form_code)
# ПутьКExchange — реквизит формы (атрибут + DataPath у поля), а не Перем модуля:
# иначе поле не к чему привязать, а одинаковые имена дают конфликт.
# 1c/АгентМост.bsl не трогаем — только артефакт сборки.
form_code_out = form_code_out.replace("&НаКлиенте\nПерем ПутьКExchange;\n", "")
form_code_out = form_code_out.replace("Перем ПутьКExchange;", "")
# Диалог прямо в 1С: сторожевой таймер читает поле «Фраза» каждую секунду.
# Без кнопок — агент отвечает сам после 4 секунд тишины.
# Диалоговое окно с нейросетью живёт в 1c/АгентМост.bsl (блок «ДИАЛОГ С
# НЕЙРОСЕТЬЮ»), реквизиты формы — ниже в form_xml.
assert "ПроверитьФразуДиалога" in form_code_out, "в .bsl нет кода диалога"

root = (DECL + NS + "\n"
        + '<ExternalDataProcessor uuid="' + EPF_UUID + '">\n'
        + "<InternalInfo>"
        + '<xr:ContainedObject><xr:ClassId>c3831ec8-d8d5-4f93-8a22-f9bfae07327f</xr:ClassId>'
        + "<xr:ObjectId>" + OBJ_UUID + "</xr:ObjectId></xr:ContainedObject>"
        + '<xr:GeneratedType name="ExternalDataProcessorObject.' + NAME + '" category="Object">'
        + "<xr:TypeId>" + TYPE_UUID + "</xr:TypeId>"
        + "<xr:ValueId>" + VALUE_UUID + "</xr:ValueId></xr:GeneratedType>"
        + "</InternalInfo>\n"
        + "<Properties><Name>" + NAME + "</Name>"
        + '<Synonym><v8:item><v8:lang></v8:lang><v8:content>' + NAME + "</v8:content></v8:item></Synonym>"
        + "<Comment>Мост агент-1С (протокол v1.0)</Comment>"
        + "<DefaultForm>ExternalDataProcessor." + NAME + ".Form.Форма</DefaultForm><AuxiliaryForm/></Properties>\n"
        + "<ChildObjects><Form>Форма</Form></ChildObjects>\n"
        + "</ExternalDataProcessor>\n</MetaDataObject>\n")

form_descr = (DECL + NS + "\n"
              + '<Form uuid="' + FORM_UUID + '">\n'
              + "<Properties><Name>Форма</Name><Synonym/><Comment/>"
              + "<FormType>Managed</FormType><IncludeHelpInContents>false</IncludeHelpInContents>"
              + "</Properties>\n</Form>\n</MetaDataObject>\n")

form_xml = (DECL + LFNS + "\n"
            + '<AutoCommandBar name="" id="-1">\n'
            + '<ButtonGroup name="ДиалогГруппа" id="-1" CommandSource="ПутьКExchange" Representation="Text"/>\n'
            + '<ButtonGroup name="ОтветыГруппа" id="-1" Representation="Text"/>\n'
            + '</AutoCommandBar>\n'
            + '<Events><Event name="OnOpen">ПриОткрытии</Event></Events>\n'
            + "<Attributes>\n"
            + '<Attribute name="Объект" id="1"><Type><v8:Type>cfg:ExternalDataProcessorObject.' + NAME + "</v8:Type></Type>"
            + "<MainAttribute>true</MainAttribute></Attribute>\n"
            + '<Attribute name="ПутьКExchange" id="2"><Type><v8:Type>xs:string</v8:Type></Type></Attribute>\n'
            + '<Attribute name="Фраза" id="3"><Type><v8:Type>xs:string</v8:Type></Type></Attribute>\n'
            + '<Attribute name="История" id="4"><Type><v8:Type>xs:string</v8:Type></Type></Attribute>\n'
            + '<Attribute name="Статус" id="5"><Type><v8:Type>xs:string</v8:Type></Type></Attribute>\n'
            + "</Attributes>\n"
            + "<Commands>\n"
            + '<Command name="ЗапуститьМост" id="1"><Title><v8:item><v8:lang>ru</v8:lang>'
            + "<v8:content>Запустить мост</v8:content></v8:item></Title>"
            + "<Action>ЗапуститьМост</Action></Command>\n"
            + '<Command name="ОстановитьМост" id="2"><Title><v8:item><v8:lang>ru</v8:lang>'
            + "<v8:content>Остановить мост</v8:content></v8:item></Title>"
            + "<Action>ОстановитьМост</Action></Command>\n"
            + "</Commands>\n"
            + "<ChildItems>\n"
            + '<InputField name="ПутьКExchange" id="10"><DataPath>ПутьКExchange</DataPath></InputField>\n'
            + '<InputField name="История" id="30"><DataPath>История</DataPath>'
            + '<MultiLine>true</MultiLine><Height>14</Height></InputField>\n'
            + '<InputField name="Фраза" id="20"><DataPath>Фраза</DataPath></InputField>\n'
            + '<InputField name="Статус" id="31"><DataPath>Статус</DataPath></InputField>\n'
            + '<UsualButton name="КнопкаЗапуститьМост" id="11">'
            + "<CommandName>ЗапуститьМост</CommandName>"
            + '<Title><v8:item><v8:lang>ru</v8:lang>'
            + "<v8:content>Запустить мост</v8:content></v8:item></Title></UsualButton>\n"
            + '<UsualButton name="КнопкаОстановитьМост" id="12">'
            + "<CommandName>ОстановитьМост</CommandName>"
            + '<Title><v8:item><v8:lang>ru</v8:lang>'
            + "<v8:content>Остановить мост</v8:content></v8:item></Title></UsualButton>\n"
            + "</ChildItems>\n"
            + "</Form>\n")

import shutil
if ROOT.exists():
    shutil.rmtree(ROOT)
(ROOT / NAME / "Forms" / "Форма" / "Ext" / "Form").mkdir(parents=True, exist_ok=True)
(ROOT / (NAME + ".xml")).write_text(root, encoding="utf-8")
(ROOT / NAME / "Forms" / "Форма.xml").write_text(form_descr, encoding="utf-8")
(ROOT / NAME / "Forms" / "Форма" / "Ext" / "Form.xml").write_text(form_xml, encoding="utf-8")
(ROOT / NAME / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl").write_text(form_code_out, encoding="utf-8")
print("most src written:", sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob("*") if p.is_file()))
print("directives in form module:", form_code_out.count("&НаКлиенте"))
