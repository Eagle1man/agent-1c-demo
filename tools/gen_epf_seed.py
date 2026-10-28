# -*- coding: utf-8 -*-
"""Генерация XML-исходников внешней обработки SeedData (заполнение демо-данных).
Структура по эталонам фикстур (managed form, logform)."""
from pathlib import Path

ROOT = Path(r"C:\1c_bases\epf_seed")
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
        'xmlns:ent="http://v8.1c.ru/8.1/data/enterprise" '
        'xmlns:lf="http://v8.1c.ru/8.2/managed-application/logform" '
        'xmlns:v8="http://v8.1c.ru/8.1/data/core" '
        'xmlns:xr="http://v8.1c.ru/8.3/xcf/readable" '
        'xmlns:xs="http://www.w3.org/2001/XMLSchema" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.4">')

import uuid as _uuid

EPF_UUID = "4b9b2a01-7c4e-4b1d-9f2a-00000000e001"
FORM_UUID = "4b9b2a01-7c4e-4b1d-9f2a-00000000e002"


def _gt5(base, objname):
    cats = ["Object", "Ref", "Selection", "List", "Manager"]
    out = "<InternalInfo>"
    for c in cats:
        out += ('<xr:GeneratedType name="' + base + c + "." + objname + '" category="' + c + '">'
                + "<xr:TypeId>" + str(_uuid.uuid4()) + "</xr:TypeId>"
                + "<xr:ValueId>" + str(_uuid.uuid4()) + "</xr:ValueId></xr:GeneratedType>")
    return out + "</InternalInfo>"


root = (DECL + NS + "\n"
        + '<ExternalDataProcessor uuid="' + EPF_UUID + '">\n'
        + _gt5("ExternalDataProcessor", "SeedData")
        + "<Properties><Name>SeedData</Name><Synonym/><Comment>Заполнение демо-данных</Comment></Properties>\n"
        + "<ChildObjects><Form>Форма</Form></ChildObjects>\n"
        + "</ExternalDataProcessor>\n</MetaDataObject>\n")

form_descr = (DECL + NS + "\n"
              + '<Form uuid="' + FORM_UUID + '">\n'
              + "<Properties><Name>Форма</Name><Synonym/><Comment/>"
              + "<FormType>Managed</FormType><IncludeHelpInContents>false</IncludeHelpInContents>"
              + "</Properties>\n</Form>\n</MetaDataObject>\n")

form_xml = (DECL + LFNS + "\n"
            + "<Events><Event name=\"OnOpen\">ПриОткрытии</Event></Events>\n"
            + "<ChildItems/>\n</Form>\n")

form_module = """Процедура ПриОткрытии(Отказ)
	Попытка
		СоздатьДемоДанные();
		ЗаписатьМаркер("OK");
	Исключение
		ЗаписатьМаркер("ERROR: " + ОписаниеОшибки());
	КонецПопытки;
	ЗавершитьРаботуСистемы(Ложь);
КонецПроцедуры

Процедура ЗаписатьМаркер(Текст)
	Зп = Новый ЗаписьТекста("C:\\1c_bases\\seed.done", КодировкаТекста.UTF8);
	Зп.Записать(Текст);
	Зп.Закрыть();
КонецПроцедуры

Функция НайтиИлиСоздатьКонтрагента(Наименование, ИНН, КПП)
	Ссылка = Справочники.Контрагенты.НайтиПоНаименованию(Наименование, Истина);
	Если Ссылка = Неопределено Или Ссылка.Пустая() Тогда
		Нов = Справочники.Контрагенты.СоздатьЭлемент();
		Нов.Наименование = Наименование;
		Нов.ИНН = ИНН;
		Нов.КПП = КПП;
		Нов.Записать();
		Возврат Нов.Ссылка;
	КонецЕсли;
	Возврат Ссылка;
КонецФункции

Функция НайтиИлиСоздатьНоменклатуру(Наименование)
	Ссылка = Справочники.Номенклатура.НайтиПоНаименованию(Наименование, Истина);
	Если Ссылка = Неопределено Или Ссылка.Пустая() Тогда
		Нов = Справочники.Номенклатура.СоздатьЭлемент();
		Нов.Наименование = Наименование;
		Нов.Записать();
		Возврат Нов.Ссылка;
	КонецЕсли;
	Возврат Ссылка;
КонецФункции

Процедура СоздатьДемоДанные()
	НайтиИлиСоздатьКонтрагента("ООО Ромашка", "7701010101", "770101001");
	НайтиИлиСоздатьКонтрагента("ООО Ветка", "7702020202", "770202001");
	НайтиИлиСоздатьКонтрагента("ИП Иванов", "770303030303", "");
	НайтиИлиСоздатьНоменклатуру("Товар А");
	НайтиИлиСоздатьНоменклатуру("Товар Б");
	НайтиИлиСоздатьНоменклатуру("Услуга монтажа");
КонецПроцедуры
"""

obj_module = """// Модуль объекта SeedData: логика в модуле формы.
"""

(ROOT / "ExternalDataProcessor" / "Forms" / "Форма" / "Ext" / "Form").mkdir(parents=True, exist_ok=True)
(ROOT / "ExternalDataProcessor" / "Ext").mkdir(parents=True, exist_ok=True)
(ROOT / "ExternalDataProcessor.xml").write_text(root, encoding="utf-8")
(ROOT / "ExternalDataProcessor" / "Forms" / "Форма.xml").write_text(form_descr, encoding="utf-8")
(ROOT / "ExternalDataProcessor" / "Forms" / "Форма" / "Ext" / "Form.xml").write_text(form_xml, encoding="utf-8")
(ROOT / "ExternalDataProcessor" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl").write_text(form_module, encoding="utf-8")
(ROOT / "ExternalDataProcessor" / "Ext" / "ObjectModule.bsl").write_text(obj_module, encoding="utf-8")
print("seed src written:", sorted(str(p) for p in ROOT.rglob("*") if p.is_file()))
