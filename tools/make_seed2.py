# -*- coding: utf-8 -*-
"""Сборка epf_seed2 из эталонного дампа: переименование + инъекция модуля и события."""
import shutil
from pathlib import Path

TPL = Path(r"C:\1c_bases\epf_tpl")
DST = Path(r"C:\1c_bases\epf_seed2")
OLD = "ВнешняяОбработка1SeedData"
NEW = "SeedData"

FORM_MODULE = """Процедура ПриОткрытии(Отказ)
\tПопытка
\t\tСоздатьДемоДанные();
\t\tЗаписатьМаркер("OK");
\tИсключение
\t\tЗаписатьМаркер("ERROR: " + ОписаниеОшибки());
\tКонецПопытки;
\tЗавершитьРаботуСистемы(Ложь);
КонецПроцедуры

Процедура ЗаписатьМаркер(Текст)
\tЗп = Новый ЗаписьТекста("C:\\1c_bases\\seed.done", КодировкаТекста.UTF8);
\tЗп.Записать(Текст);
\tЗп.Закрыть();
КонецПроцедуры

Функция НайтиИлиСоздатьКонтрагента(Наименование, ИНН, КПП)
\tСсылка = Справочники.Контрагенты.НайтиПоНаименованию(Наименование, Истина);
\tЕсли Ссылка = Неопределено Или Ссылка.Пустая() Тогда
\t\tНов = Справочники.Контрагенты.СоздатьЭлемент();
\t\tНов.Наименование = Наименование;
\t\tНов.ИНН = ИНН;
\t\tНов.КПП = КПП;
\t\tНов.Записать();
\t\tВозврат Нов.Ссылка;
\tКонецЕсли;
\tВозврат Ссылка;
КонецФункции

Функция НайтиИлиСоздатьНоменклатуру(Наименование)
\tСсылка = Справочники.Номенклатура.НайтиПоНаименованию(Наименование, Истина);
\tЕсли Ссылка = Неопределено Или Ссылка.Пустая() Тогда
\t\tНов = Справочники.Номенклатура.СоздатьЭлемент();
\t\tНов.Наименование = Наименование;
\t\tНов.Записать();
\t\tВозврат Нов.Ссылка;
\tКонецЕсли;
\tВозврат Ссылка;
КонецФункции

Процедура СоздатьДемоДанные()
\tНайтиИлиСоздатьКонтрагента("ООО Ромашка", "7701010101", "770101001");
\tНайтиИлиСоздатьКонтрагента("ООО Ветка", "7702020202", "770202001");
\tНайтиИлиСоздатьКонтрагента("ИП Иванов", "770303030303", "");
\tНайтиИлиСоздатьНоменклатуру("Товар А");
\tНайтиИлиСоздатьНоменклатуру("Товар Б");
\tНайтиИлиСоздатьНоменклатуру("Услуга монтажа");
КонецПроцедуры
"""

if DST.exists():
    shutil.rmtree(DST)
shutil.copytree(TPL, DST)
# переименовать корень и каталог объекта
roots = list(DST.glob("*.xml"))
assert len(roots) == 1, roots
roots[0].rename(DST / (NEW + ".xml"))
subdirs = [d for d in DST.iterdir() if d.is_dir()]
assert len(subdirs) == 1, subdirs
subdirs[0].rename(DST / NEW)
# заменить имя во всех файлах
for f in DST.rglob("*"):
    if f.is_file():
        try:
            t = f.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if OLD in t:
            f.write_text(t.replace(OLD, NEW), encoding="utf-8")
# инъекция события OnOpen в Form.xml
form_xml = DST / NEW / "Forms" / "Форма" / "Ext" / "Form.xml"
t = form_xml.read_text(encoding="utf-8")
anchor = '<AutoCommandBar name="" id="-1"/>'
assert anchor in t
t = t.replace(anchor, anchor + '\n\t<Events><Event name="OnOpen">ПриОткрытии</Event></Events>')
form_xml.write_text(t, encoding="utf-8")
# модуль формы
(DB := DST / NEW / "Forms" / "Форма" / "Ext" / "Form").mkdir(parents=True, exist_ok=True)
(DB / "Module.bsl").write_text(FORM_MODULE, encoding="utf-8")
print("seed2 ready:", sorted(str(p.relative_to(DST)) for p in DST.rglob("*") if p.is_file()))
