import psycopg2
c = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
r = c.cursor()

# Test different query approaches
texts = [
    "LIVA Autoliquidacion modelo 303 Los sujetos pasarios estaran obligados a presentar autoliquidaciones trimestrales",
]

queries = [
    "Autoliquidacion trimestral IVA modelo 303",
    "Autoliquidacion",
    "autoliquidacion",
]

for q in queries:
    r.execute("SELECT plainto_tsquery('spanish', %s)", (q,))
    pq = r.fetchone()[0]
    print(f"plainto_tsquery('{q}') = {pq}")

    r.execute("SELECT websearch_to_tsquery('spanish', %s)", (q,))
    wq = r.fetchone()[0]
    print(f"websearch_to_tsquery('{q}') = {wq}")

    # Check accent restoration
    accent_q = q.replace('autoliquidacion', 'autoliquidación')
    r.execute("SELECT websearch_to_tsquery('spanish', %s)", (accent_q,))
    wqa = r.fetchone()[0]
    print(f"websearch_to_tsquery('{accent_q}') = {wqa}")

    # Test matching with each
    for text in texts:
        r.execute("SELECT to_tsvector('spanish', %s)", (text,))
        tv = r.fetchone()[0]
        r.execute("SELECT to_tsvector('spanish', %s) @@ plainto_tsquery('spanish', %s)", (text, q))
        match_pq = r.fetchone()[0]
        r.execute("SELECT to_tsvector('spanish', %s) @@ websearch_to_tsquery('spanish', %s)", (text, q))
        match_wq = r.fetchone()[0]
        r.execute("SELECT to_tsvector('spanish', %s) @@ websearch_to_tsquery('spanish', %s)", (text, accent_q))
        match_wqa = r.fetchone()[0]
        print(f"  vector matches plainto: {match_pq}, websearch: {match_wq}, websearch+accent: {match_wqa}")

    print()

c.close()
