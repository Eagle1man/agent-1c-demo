from pathlib import Path

root = Path(r"D:\agent-1c-demo")
src = root / "1c" / "АгентМост.bsl"
dst = root / "build" / "epf_src" / "АгентМост" / "Forms" / "Форма" / "Ext" / "Form" / "Module.bsl"

text = src.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\n", "\r\n")
# 1C ожидает модуль в UTF-8 с BOM внутри выгрузки
dst.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))
print("записан модуль:", dst)
print("байт:", dst.stat().st_size)
