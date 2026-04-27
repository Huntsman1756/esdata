import pathlib

files = [
    "ingest_crs_fatca.py",
    "ingest_w8_forms.py",
    "ingest_tin_europa.py",
    "ingest_convenios.py",
]

for f in files:
    p = pathlib.Path(f)
    text = p.read_text(encoding="utf-8")
    text = text.replace('psycopg.ADAPTERS["date"].adapt(', '')
    text = text.replace('")', ')')
    p.write_text(text, encoding="utf-8")
    print(f"Fixed: {f}")
