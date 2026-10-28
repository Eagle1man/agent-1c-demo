# -*- coding: utf-8 -*-
"""SeedData2: богатые демо-данные как у живой фирмы (контрагенты, номенклатура,
~50 реализаций за июль–сентябрь 2026). Идемпотентно через маркер seed2.done."""
from pathlib import Path

ROOT = Path(r"C:\1c_bases\epf_seed2")
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
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="2.20">')

EPF_UUID = "4b9b2a01-7c4e-4b1d-9f2a-00000000e201"
FORM_UUID = "4b9b2a01-7c4e-4b1d-9f2a-00000000e202"

root = (DECL + NS + "\n"
        + '<ExternalDataProcessor uuid="' + EPF_UUID + '">\n'
        + "<InternalInfo>"
        + '<xr:ContainedObject><xr:ClassId>c3831ec8-d8d5-4f93-8a22-f9bfae07327f</xr:ClassId>'
        + "<xr:ObjectId>4b9b2a01-7c4e-4b1d-9f2a-00000000e203</xr:ObjectId></xr:ContainedObject>"
        + '<xr:GeneratedType name="ExternalDataProcessorObject.SeedData2" category="Object">'
        + "<xr:TypeId>4b9b2a01-7c4e-4b1d-9f2a-00000000e204</xr:TypeId>"
        + "<xr:ValueId>4b9b2a01-7c4e-4b1d-9f2a-00000000e205</xr:ValueId></xr:GeneratedType>"
        + "</InternalInfo>\n"
        + "<Properties><Name>SeedData2</Name>"
        + '<Synonym><v8:item><v8:lang></v8:lang><v8:content>SeedData2</v8:content></v8:item></Synonym>'
        + "<Comment>Богатые демо-данные</Comment>"
        + "<DefaultForm>ExternalDataProcessor.SeedData2.Form.Форма</DefaultForm><AuxiliaryForm/></Properties>\n"
        + "<ChildObjects><Form>Форма</Form></ChildObjects>\n"
        + "</ExternalDataProcessor>\n</MetaDataObject>\n")

form_descr = (DECL + NS + "\n"
              + '<Form uuid="' + FORM_UUID + '">\n'
              + "<Properties><Name>Форма</Name><Synonym/><Comment/>"
              + "<FormType>Managed</FormType><IncludeHelpInContents>false</IncludeHelpInContents>"
              + "</Properties>\n</Form>\n</MetaDataObject>\n")

form_xml = (DECL + LFNS + "\n"
            + '<Events><Event name="OnOpen">ПриОткрытии</Event></Events>\n'
            + "<ChildItems/>\n</Form>\n")

parties = [
    ("ООО Ромашка", "7701010101", "770101001"),
    ("ООО Ветка", "7702020202", "770202001"),
    ("ИП Иванов", "770303030303", ""),
    ("ООО Лютик", "7704040404", "770404001"),
    ("АО Заря", "7705050505", "770505001"),
    ("ИП Петрова", "770606060606", ""),
    ("ООО Меридиан", "7707070707", "770707001"),
    ("ЗАО Горизонт", "7708080808", "770808001"),
    ("ИП Сидоров", "770909090909", ""),
    ("ООО Клевер", "7710101010", "771010001"),
    ("ПАО Восток", "7711111111", "771111001"),
    ("ИП Кузнецова", "771212121212", ""),
]
items = ["Товар А", "Товар Б", "Товар В", "Товар Г", "Товар Д",
         "Комплект Офис", "Комплект Склад", "Услуга монтажа", "Услуга доставки",
         "Услуга пусконаладки", "Запчасть 101", "Запчасть 102", "Запчасть 103",
         "Кабель 5м", "Кабель 10м", "Крепёж М8", "Крепёж М10",
         "Светильник ЛПО", "Розетка двойная", "Выключатель"]


def bsl_str(s):
    return '"' + s.replace('"', '""') + '"'


lines = []
lines.append("&НаКлиенте\nПроцедура ПриОткрытии(Отказ)")
lines.append("\tПопытка")
lines.append("\t\tСоздатьДемоДанные();")
lines.append('\t\tЗаписатьМаркер("OK");')
lines.append("\tИсключение")
lines.append('\t\tЗаписатьМаркер("ERROR: " + ОписаниеОшибки());')
lines.append("\tКонецПопытки;")
lines.append("\tЗавершитьРаботуСистемы(Ложь);")
lines.append("КонецПроцедуры\n")
lines.append("&НаКлиенте\nПроцедура ЗаписатьМаркер(Текст)")
lines.append('\tЗп = Новый ЗаписьТекста("C:\\\\1c_bases\\\\seed2.done", КодировкаТекста.UTF8);')
lines.append("\tЗп.Записать(Текст);")
lines.append("\tЗп.Закрыть();")
lines.append("КонецПроцедуры\n")
lines.append("&НаКлиенте\nФункция НайтиИлиСоздатьКонтрагента(Наименование, ИНН, КПП)")
lines.append("\tСсылка = Справочники.Контрагенты.НайтиПоНаименованию(Наименование, Истина);")
lines.append("\tЕсли Ссылка = Неопределено Или Ссылка.Пустая() Тогда")
lines.append("\t\tНов = Справочники.Контрагенты.СоздатьЭлемент();")
lines.append("\t\tНов.Наименование = Наименование;")
lines.append("\t\tНов.ИНН = ИНН;")
lines.append("\t\tНов.КПП = КПП;")
lines.append("\t\tНов.Записать();")
lines.append("\t\tВозврат Нов.Ссылка;")
lines.append("\tКонецЕсли;")
lines.append("\tВозврат Ссылка;")
lines.append("КонецФункции\n")
lines.append("&НаКлиенте\nФункция НайтиИлиСоздатьНоменклатуру(Наименование)")
lines.append("\tСсылка = Справочники.Номенклатура.НайтиПоНаименованию(Наименование, Истина);")
lines.append("\tЕсли Ссылка = Неопределено Или Ссылка.Пустая() Тогда")
lines.append("\t\tНов = Справочники.Номенклатура.СоздатьЭлемент();")
lines.append("\t\tНов.Наименование = Наименование;")
lines.append("\t\tНов.Записать();")
lines.append("\t\tВозврат Нов.Ссылка;")
lines.append("\tКонецЕсли;")
lines.append("\tВозврат Ссылка;")
lines.append("КонецФункции\n")
lines.append("&НаКлиенте\nПроцедура СоздатьДемоДанные()")
for nm, inn, kpp in parties:
    lines.append(f"\tНайтиИлиСоздатьКонтрагента({bsl_str(nm)}, {bsl_str(inn)}, {bsl_str(kpp)});")
for nm in items:
    lines.append(f"\tНайтиИлиСоздатьНоменклатуру({bsl_str(nm)});")
lines.append("\tОчиститьРеализации();")
# ~2 года: 10.2024–09.2026, ~350 документов с ростом к концу
import hashlib
from datetime import date
n = 0
dd = date(2024, 10, 1)
d1 = date(2026, 9, 26)
while dd <= d1:
    h = int(hashlib.md5(f"doc{dd}".encode()).hexdigest(), 16)
    recent = (dd.year * 12 + dd.month) - (2024 * 12 + 10)
    keep = 44 + recent  # рост активности: ~44% -> ~68%
    if h % 100 < keep:
        pi = h % len(parties)
        n += 1
        lines.append(f"\tСоздатьРеализацию({dd.year}, {dd.month}, {dd.day}, {bsl_str(parties[pi][0])}, {n});")
    dd = date.fromordinal(dd.toordinal() + 1)
lines.append("КонецПроцедуры\n")
lines.append("&НаКлиенте\nПроцедура ОчиститьРеализации()")
lines.append("\tПопытка")
lines.append("\t\tВ = Документы.РеализацияТоваровУслуг.Выбрать();")
lines.append("\t\tПока В.Следующий() Цикл")
lines.append("\t\t\tПопытка")
lines.append("\t\t\t\tВ.ПолучитьОбъект().Удалить();")
lines.append("\t\t\tИсключение")
lines.append("\t\t\tКонецПопытки;")
lines.append("\t\tКонецЦикла;")
lines.append("\tИсключение")
lines.append("\tКонецПопытки;")
lines.append("КонецПроцедуры\n")
lines.append("&НаКлиенте\nПроцедура СоздатьРеализацию(ГодДок, МесДок, ДеньДок, НаимКонтр, Сдвиг)")
lines.append("\tПопытка")
lines.append("\t\tКонтр = Справочники.Контрагенты.НайтиПоНаименованию(НаимКонтр, Истина);")
lines.append("\t\tЕсли Контр = Неопределено Или Контр.Пустая() Тогда Возврат; КонецЕсли;")
lines.append("\t\tНов = Документы.РеализацияТоваровУслуг.СоздатьДокумент();")
lines.append("\t\tНов.Дата = Дата(ГодДок, МесДок, ДеньДок, 12, 0, 0);")
lines.append("\t\tНов.Контрагент = Контр;")
lines.append("\t\tВсегоПоз = 1 + (Сдвиг % 3);")
lines.append("\t\tДля И_ = 1 По ВсегоПоз Цикл")
lines.append('\t\t\tНом = НайтиИлиСоздатьНоменклатуру(СокрЛП("Товар " + Символ(1040 + ((Сдвиг + И_) % 5))));')
lines.append("\t\t\tСтр = Нов.Товары.Добавить();")
lines.append("\t\t\tСтр.Номенклатура = Ном;")
lines.append("\t\t\tСтр.Количество = 1 + ((Сдвиг * 7 + И_ * 3) % 20);")
lines.append("\t\t\tСтр.Цена = 100 + ((Сдвиг * 137 + И_ * 53) % 4900);")
lines.append("\t\tКонецЦикла;")
lines.append("\t\tНов.Записать(РежимЗаписиДокумента.Проведение);")
lines.append("\tИсключение")
lines.append("\tКонецПопытки;")
lines.append("КонецПроцедуры\n")
form_module = "\n".join(lines)

obj_module = "// Модуль объекта SeedData2: логика в модуле формы.\n"

import shutil
if ROOT.exists():
    shutil.rmtree(ROOT)
(ROOT / "SeedData2" / "Forms" / "Форма" / "Ext" / "Form").mkdir(parents=True, exist_ok=True)
(ROOT / "SeedData2" / "Ext").mkdir(parents=True, exist_ok=True)
(ROOT / "SeedData2.xml").write_text(root, encoding="utf-8")
(ROOT / "SeedData2" / "Forms" / "Форма.xml").write_text(form_descr, encoding="utf-8")
(ROOT / "SeedData2" / "Forms" / "Форма" / "Ext" / "Form.xml").write_text(form_xml, encoding="utf-8")
(ROOT / "SeedData2" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl").write_text(form_module, encoding="utf-8")
(ROOT / "SeedData2" / "Ext" / "ObjectModule.bsl").write_text(obj_module, encoding="utf-8")
print("seed2 src written")
