# -*- coding: utf-8 -*-
"""Генерация XML-исходников конфигурации ДемоАгент v2.
По эталонам из открытых фикстур (files-format, version 2.20):
- файлы и ссылки ChildObjects — по ИМЕНАМ объектов;
- InternalInfo: Configuration = 7 системных записей verbatim из выгрузки базы;
  Catalog/Document = 5 GeneratedType; TabularSection = 2 GeneratedType;
  Attribute = без InternalInfo;
- типы: xs:string/xs:decimal + Digits/FractionDigits; ссылки cfg:CatalogRef.X.
UUID стабильны: НЕ менять между итерациями."""
from pathlib import Path

ROOT = Path(r"C:\1c_bases\cfg_src")
DECL = '<?xml version="1.0" encoding="utf-8"?>\n'
T = "\t"
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

_TIDS = ['95c2ef3f-aa79-499d-9a4a-74ef4567fae0', '2a38f156-d8c3-4624-aced-df9108bb2716', '0b2adf99-81b4-406c-9640-2ecddd2641b4', 'adfb401b-3f93-4b5d-b72e-10bf7b494f80', '4f0c8fb1-645a-4294-8332-8ec8df415384', '1c2e8be5-5a43-4150-a8a9-dde5c170303e', '55345caf-13a2-41c8-ac07-1dca38cd648b', '54463a95-bfcc-4b7f-9e14-fbe5a34019a0', '19c31f6f-4f23-4921-8a85-89e517028623', '97677835-6ea5-4e1c-86ff-6e1dcd734b6b', '7d144f12-4355-445e-9df5-a52a2da7b6c9', 'e5176488-3434-459d-b071-2e47b7c35fb3', 'a93da3c7-a886-4534-8bf2-6508b7356dfa', 'e3a672c1-afa3-49aa-bacf-4008fb9caf47', '77873974-80d2-4605-9333-fbc1275ad711', '7cf02857-3e5c-4017-9dc4-cb292c6d440c', 'a0d9c6b9-d6f5-43d1-a3af-5c1e4bb95491']
_tid_i = [0]


def _tid():
    v = _TIDS[_tid_i[0] % len(_TIDS)]
    _tid_i[0] += 1
    return v


ZERO = "00000000-0000-0000-0000-000000000000"


V = {  # свежие ValueId (стабильны между итерациями)
    "k_obj": "6f839c48-79fc-48ae-a852-c595fbc83a57",
    "k_ref": "c05283d0-25cd-405d-ba22-e734adfae1ec",
    "k_sel": "f3e27f0d-8ca2-4947-a5a1-d7f12e79af5e",
    "k_list": "fb539bc0-f7dc-47bf-899a-86f96aec46c8",
    "k_mgr": "9a0d9e78-1569-4780-bda7-263920e39085",
    "n_obj": "0fc4a1f2-f003-4239-ba7d-43e75bb0b4c1",
    "n_ref": "0e268620-917d-479c-9036-80f9d2483729",
    "n_sel": "0c1847a7-8675-4ed9-a818-bf8ca8c50e63",
    "n_list": "37f27809-d500-4375-a344-12ca9e610b64",
    "n_mgr": "cdc3dc2f-8544-4b0b-b2f7-00d610edd442",
    "d_obj": "9a7dacea-7cad-4efc-a1ba-dc037b1087e3",
    "d_ref": "b842a867-65a9-454c-9947-4fe1517d760a",
    "d_sel": "6c19344f-f304-4012-ae9d-c369635ef902",
    "d_list": "7a9ca160-2175-4f78-9aed-43b0e42fd063",
    "d_mgr": "b7b4d136-8e92-4c22-b096-3920e7fc7bdf",
    "t_ts": "b7d953c2-9350-4832-bb4b-1cf6e19bc668",
    "t_row": "d5563067-3658-4cff-a24c-c95714449548",
}

G = {
    "catalog_k": "3b9b2a01-7c4e-4b1d-9f2a-000000000001",
    "attr_inn": "3b9b2a01-7c4e-4b1d-9f2a-000000000002",
    "attr_kpp": "3b9b2a01-7c4e-4b1d-9f2a-000000000003",
    "catalog_n": "3b9b2a01-7c4e-4b1d-9f2a-000000000004",
    "doc": "3b9b2a01-7c4e-4b1d-9f2a-000000000005",
    "doc_attr": "3b9b2a01-7c4e-4b1d-9f2a-000000000006",
    "ts": "3b9b2a01-7c4e-4b1d-9f2a-000000000007",
    "ts_nomen": "3b9b2a01-7c4e-4b1d-9f2a-000000000008",
    "ts_qty": "3b9b2a01-7c4e-4b1d-9f2a-000000000009",
    "ts_price": "3b9b2a01-7c4e-4b1d-9f2a-000000000010",
}

import re as _re
_dump = Path(r"C:\1c_bases\empty_dump\Configuration.xml").read_text(encoding="utf-8")
SYS7 = _re.search("<InternalInfo>.*?</InternalInfo>", _dump, flags=_re.S).group(0)


def gt5(prefix, objname, vkeys):
    raise RuntimeError("unused")


def syn(name):
    return ("<Synonym><v8:item><v8:lang>ru</v8:lang>"
            "<v8:content>" + name + "</v8:content></v8:item></Synonym>")


BASE_ATTRS = """<PasswordMode>false</PasswordMode><Format/><EditFormat/><ToolTip/><MarkNegatives>false</MarkNegatives><Mask/><MultiLine>false</MultiLine><ExtendedEdit>false</ExtendedEdit><MinValue xsi:nil="true"/><MaxValue xsi:nil="true"/><FillChecking>DontCheck</FillChecking><ChoiceFoldersAndItems>Items</ChoiceFoldersAndItems><ChoiceParameterLinks/><ChoiceParameters/><QuickChoice>Auto</QuickChoice><CreateOnInput>Auto</CreateOnInput><ChoiceForm/><LinkByType/><ChoiceHistoryOnInput>Auto</ChoiceHistoryOnInput><Indexing>DontIndex</Indexing><FullTextSearch>Use</FullTextSearch>"""


def attr_str(uuid, name, length):
    return ('<Attribute uuid="' + uuid + '"><Properties><Name>' + name + "</Name>" + syn(name)
            + "<Comment/><Type><v8:Type>xs:string</v8:Type><v8:StringQualifiers><v8:Length>"
            + str(length) + "</v8:Length><v8:AllowedLength>Variable</v8:AllowedLength>"
            "</v8:StringQualifiers></Type>" + BASE_ATTRS + "</Properties></Attribute>")


def attr_ref(uuid, name, ref):
    return ('<Attribute uuid="' + uuid + '"><Properties><Name>' + name + "</Name>" + syn(name)
            + "<Comment/><Type><v8:Type>" + ref + "</v8:Type></Type>" + BASE_ATTRS
            + "</Properties></Attribute>")


def attr_dec(uuid, name, digits, frac):
    return ('<Attribute uuid="' + uuid + '"><Properties><Name>' + name + "</Name>" + syn(name)
            + "<Comment/><Type><v8:Type>xs:decimal</v8:Type><v8:NumberQualifiers><v8:Digits>"
            + str(digits) + "</v8:Digits><v8:FractionDigits>" + str(frac) + "</v8:FractionDigits>"
            '<v8:AllowedSign>Any</v8:AllowedSign></v8:NumberQualifiers></Type>' + BASE_ATTRS
            + "</Properties></Attribute>")


CAT_PROPS = """<Hierarchical>false</Hierarchical><HierarchyType>HierarchyFoldersAndItems</HierarchyType><LimitLevelCount>false</LimitLevelCount><LevelCount>2</LevelCount><FoldersOnTop>true</FoldersOnTop><UseStandardCommands>true</UseStandardCommands><Owners/><SubordinationUse>ToItems</SubordinationUse><CodeLength>9</CodeLength><DescriptionLength>100</DescriptionLength><CodeType>String</CodeType><CodeAllowedLength>Variable</CodeAllowedLength><CodeSeries>WholeCatalog</CodeSeries><CheckUnique>true</CheckUnique><Autonumbering>true</Autonumbering><DefaultPresentation>AsDescription</DefaultPresentation><Characteristics/><PredefinedDataUpdate>Auto</PredefinedDataUpdate><EditType>InDialog</EditType><QuickChoice>false</QuickChoice><ChoiceMode>BothWays</ChoiceMode><IncludeHelpInContents>false</IncludeHelpInContents><BasedOn/><DataLockFields/><DataLockControlMode>Managed</DataLockControlMode><FullTextSearch>Use</FullTextSearch><CreateOnInput>Use</CreateOnInput><ChoiceHistoryOnInput>Auto</ChoiceHistoryOnInput><DataHistory>DontUse</DataHistory>"""


def catalog_xml(*a, **k):
    raise RuntimeError("unused")


def catalog_ii(name, vk5):
    cats = ["Object", "Ref", "Selection", "List", "Manager"]
    out = "<InternalInfo>"
    for c, vk in zip(cats, vk5):
        out += ('<xr:GeneratedType name="Catalog' + c + "." + name + '" category="' + c + '">'
                + "<xr:TypeId>" + _tid() + "</xr:TypeId>"
                + "<xr:ValueId>" + V[vk] + "</xr:ValueId></xr:GeneratedType>")
    return out + "</InternalInfo>"


def doc_ii(name, vk5):
    cats = ["Object", "Ref", "Selection", "List", "Manager"]
    out = "<InternalInfo>"
    for c, vk in zip(cats, vk5):
        out += ('<xr:GeneratedType name="Document' + c + "." + name + '" category="' + c + '">'
                + "<xr:TypeId>" + _tid() + "</xr:TypeId>"
                + "<xr:ValueId>" + V[vk] + "</xr:ValueId></xr:GeneratedType>")
    return out + "</InternalInfo>"


def ts_ii(docname, tsname):
    return ("<InternalInfo>"
            '<xr:GeneratedType name="DocumentTabularSection.' + docname + "." + tsname + '" category="TabularSection">'
            + "<xr:TypeId>" + _tid() + "</xr:TypeId>"
            + "<xr:ValueId>" + V["t_ts"] + "</xr:ValueId></xr:GeneratedType>"
            '<xr:GeneratedType name="DocumentTabularSectionRow.' + docname + "." + tsname + '" category="TabularSectionRow">'
            + "<xr:TypeId>" + _tid() + "</xr:TypeId>"
            + "<xr:ValueId>" + V["t_row"] + "</xr:ValueId></xr:GeneratedType>"
            + "</InternalInfo>")


DOC_PROPS = """<UseStandardCommands>true</UseStandardCommands><Numerator/><NumberType>String</NumberType><NumberLength>9</NumberLength><NumberAllowedLength>Variable</NumberAllowedLength><NumberPeriodicity>Nonperiodical</NumberPeriodicity><CheckUnique>true</CheckUnique><Autonumbering>true</Autonumbering><Characteristics/><BasedOn/><CreateOnInput>Use</CreateOnInput><Posting>Allow</Posting><RealTimePosting>Allow</RealTimePosting><RegisterRecordsDeletion>AutoDeleteOnUnpost</RegisterRecordsDeletion><RegisterRecordsWritingOnPost>WriteSelected</RegisterRecordsWritingOnPost><SequenceFilling>AutoFill</SequenceFilling><PostInPrivilegedMode>true</PostInPrivilegedMode><UnpostInPrivilegedMode>true</UnpostInPrivilegedMode><IncludeHelpInContents>false</IncludeHelpInContents><DataLockFields/><DataLockControlMode>Managed</DataLockControlMode><FullTextSearch>Use</FullTextSearch><ChoiceHistoryOnInput>Auto</ChoiceHistoryOnInput>"""

TS_PROPS = "<ToolTip/><FillChecking>DontCheck</FillChecking>"

catalog_k = (DECL + NS + "\n" + '<Catalog uuid="' + G["catalog_k"] + '">'
             + catalog_ii("Контрагенты", ["k_obj", "k_ref", "k_sel", "k_list", "k_mgr"])
             + "<Properties><Name>Контрагенты</Name>" + syn("Контрагенты") + "<Comment/>" + CAT_PROPS + "</Properties>"
             + "<ChildObjects>" + attr_str(G["attr_inn"], "ИНН", 12) + attr_str(G["attr_kpp"], "КПП", 9)
             + "</ChildObjects></Catalog></MetaDataObject>\n")

catalog_n = (DECL + NS + "\n" + '<Catalog uuid="' + G["catalog_n"] + '">'
             + catalog_ii("Номенклатура", ["n_obj", "n_ref", "n_sel", "n_list", "n_mgr"])
             + "<Properties><Name>Номенклатура</Name>" + syn("Номенклатура") + "<Comment/>" + CAT_PROPS + "</Properties>"
             + "<ChildObjects/></Catalog></MetaDataObject>\n")

doc_r = (DECL + NS + "\n" + '<Document uuid="' + G["doc"] + '">'
         + doc_ii("РеализацияТоваровУслуг", ["d_obj", "d_ref", "d_sel", "d_list", "d_mgr"])
         + "<Properties><Name>РеализацияТоваровУслуг</Name>" + syn("Реализация товаров и услуг") + "<Comment/>" + DOC_PROPS + "</Properties>"
         + "<ChildObjects>" + attr_ref(G["doc_attr"], "Контрагент", "cfg:CatalogRef.Контрагенты")
         + '<TabularSection uuid="' + G["ts"] + '">' + ts_ii("РеализацияТоваровУслуг", "Товары")
         + "<Properties><Name>Товары</Name>" + syn("Товары") + "<Comment/>" + TS_PROPS + "</Properties>"
         + "<ChildObjects>" + attr_ref(G["ts_nomen"], "Номенклатура", "cfg:CatalogRef.Номенклатура")
         + attr_dec(G["ts_qty"], "Количество", 15, 3) + attr_dec(G["ts_price"], "Цена", 15, 2)
         + "</ChildObjects></TabularSection>"
         + "</ChildObjects></Document></MetaDataObject>\n")

config = (DECL + NS + "\n"
          + '<Configuration uuid="3b9b2a01-7c4e-4b1d-9f2a-00000000cafe">' + SYS7
          + "<Properties><Name>ДемоАгент</Name>" + syn("ДемоАгент")
          + "<Comment>Минимальная конфигурация для демо ИИ-агента</Comment>"
          + "<ScriptVariant>Russian</ScriptVariant>"
          + "<DefaultLanguage>Language.Русский</DefaultLanguage></Properties>"
          + "<ChildObjects><Language>Русский</Language><Catalog>Контрагенты</Catalog><Catalog>Номенклатура</Catalog>"
          + "<Document>РеализацияТоваровУслуг</Document></ChildObjects>"
          + "</Configuration></MetaDataObject>\n")

(ROOT / "Catalogs").mkdir(parents=True, exist_ok=True)
(ROOT / "Documents").mkdir(parents=True, exist_ok=True)
for f in list((ROOT / "Catalogs").glob("*.xml")) + list((ROOT / "Documents").glob("*.xml")):
    f.unlink()
(ROOT / "Configuration.xml").write_text(config, encoding="utf-8")
(ROOT / "Catalogs" / "Контрагенты.xml").write_text(catalog_k, encoding="utf-8")
(ROOT / "Catalogs" / "Номенклатура.xml").write_text(catalog_n, encoding="utf-8")
(ROOT / "Documents" / "РеализацияТоваровУслуг.xml").write_text(doc_r, encoding="utf-8")
print("v2 written:", sorted(str(p) for p in ROOT.rglob("*.xml")))
