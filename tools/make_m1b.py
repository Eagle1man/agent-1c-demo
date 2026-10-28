# -*- coding: utf-8 -*-
"""M1b: минимальный модуль БЕЗ директивы перед Перем (точечная проверка гипотезы)."""
from pathlib import Path

p = Path(r"C:\1c_bases\epf_m1\M1\Forms\Форма\Ext\Form\Module.bsl")
p.write_text("Перем ПутьКExchange;\n\n&НаКлиенте\nПроцедура ПриОткрытии(Отказ)\n"
             '\tПутьКExchange = "C:\\1c_bases\\x";\nКонецПроцедуры\n', encoding="utf-8")
print("m1b module ok")
