import psycopg2
import re

conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

def _add_accents(text):
    accent_fixes = {
        'autoliquidacion': 'autoliquidación',
        'declaracion': 'declaración',
        'hacienda': 'hacienda',
    }
    words = re.findall(r"[\w]+", text.lower())
    result = text
    for word in words:
        if word in accent_fixes:
            result = result.replace(word, accent_fixes[word])
    return result

def build_tsquery(value):
    normalized = _add_accents(value)
    words = re.findall(r"[\wáéíóúüñ]+", normalized, flags=re.IGNORECASE)
    
    or_map = {
        'iva': ['iva', 'liv'],
        'irnr': ['irnr', 'noresident'],
        'lirnr': ['lirnr', 'irnr', 'noresident'],
        'dac6': ['dac6', 'transfronteriz', 'mecanis'],
        'itp': ['itp', 'patrim'],
        'ajd': ['ajd', 'document'],
        'sepblac': ['sepblac', 'lavado', 'capitales'],
        'cnmv': ['cnmv', 'mercados', 'valores'],
        'hacienda': ['hacienda', 'hacendari'],
        'blanqueo': ['blanqueo', 'lavado'],
        'blanquear': ['blanquear', 'lavado'],
        'lis': ['lis', 'socied'],
    }
    
    # Get stems for each word via plainto_tsquery
    all_terms = []
    for w in words:
        w_lower = w.lower()
        if w_lower in or_map:
            # Get stem for first alternative, then add others as OR
            cur.execute("SELECT plainto_tsquery('spanish', %s)", (w,))
            stem = cur.fetchone()[0]
            all_terms.append(f"({stem} | " + " | ".join(f"'{alt}'" for alt in or_map[w_lower]) + ")")
        else:
            cur.execute("SELECT plainto_tsquery('spanish', %s)", (w,))
            stem = cur.fetchone()[0]
            all_terms.append(stem)
    
    return " & ".join(all_terms)

# Test queries
tests = [
    ("LIVA", "Autoliquidacion trimestral iva modelo 303", "LIVA", "123"),
    ("IRPF", "Declaracion anual irpf modelo 100", "LIRPF", "124"),
    ("IRNR", "No residente rentas inmobiliarias modelo 216", "LIRNR", "123"),
    ("LGT", "Obligaciones formales tributarias LGT", "LGT", "56"),
]

for name, query, norma, art in tests:
    tsq = build_tsquery(query)
    print(f"\n=== {name}: {query}")
    print(f"  tsquery: {tsq}")
    
    cur.execute(f"""
        SELECT cf.search_vector @@ ({tsq}) as match_test
        FROM documento_fragmento cf
        WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo=%s) AND numero=%s)
        LIMIT 1
    """, (norma, art))
    result = cur.fetchone()[0]
    print(f"  match: {result}")
    
    cur.execute("""
        SELECT cf.search_vector FROM documento_fragmento cf
        WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo=%s) AND numero=%s)
        LIMIT 1
    """, (norma, art))
    vec = cur.fetchone()[0]
    print(f"  vector: {vec}")

conn.close()
