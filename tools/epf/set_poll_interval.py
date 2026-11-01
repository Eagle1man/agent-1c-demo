from pathlib import Path

p = Path(r"D:\agent-1c-demo") / "1c" / "АгентМост.bsl"
raw = p.read_bytes()
has_bom = raw.startswith(b"\xef\xbb\xbf")
text = raw.decode("utf-8-sig")

old = '"ОпросОчереди", 2'
new = '"ОпросОчереди", 1'
count = text.count(old)
text = text.replace(old, new)
text = text.replace("каждые 2 сек", "каждую 1 сек")

data = text.encode("utf-8")
if has_bom:
    data = b"\xef\xbb\xbf" + data
p.write_bytes(data)
print("заменено интервалов опроса:", count)
