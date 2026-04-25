import psycopg2
import re

conn = psycopg2.connect('dbname=esdata user=esdata password=testpass host=localhost port=5434')
cur = conn.cursor()

def _add_accents(text):
    accent_fixes = {
        'autoliquidacion': 'autoliquidación',
        'declaracion': 'declaración',
    }
    words = re.findall(r"[\w]+", text.lower())
    result = text
    for word in words:
        if word in accent_fixes:
            result = result.replace(word, accent_fixes[word])
    return result

def build_tsquery(value):
    """Build tsquery using plainto_tsquery for stemming + OR for abbreviations.
    
    Each word is stemmed via plainto_tsquery('spanish', word).
    Abbreviations get OR expansions: (stem | alt1 | alt2).
    The result is a clean string like: 'autoliquid' & 'trimestral' & (iva | liv) & 'model' & '303'
    that can be cast with ::tsquery.
    """
    normalized = _add_accents(value)
    words = re.findall(r"[\wáéíóúüñ]+", normalized, flags=re.IGNORECASE)
    
    or_map = {
        'iva': ['liv'],
        'liva': ['liv'],
        'riva': ['liv'],
        'irnr': ['noresident'],
        'lirnr': ['noresident'],
        'dac6': ['transfronteriz', 'mecanis'],
        'itp': ['patrim'],
        'ajd': ['document'],
        'itpajd': ['patrim', 'document'],
        'sepblac': ['lavado', 'capitales'],
        'cnmv': ['mercados', 'valores'],
        'hacienda': ['hacendari'],
        'blanqueo': ['lavado'],
        'blanquear': ['lavado'],
        'lis': ['socied'],
    }
    
    parts = []
    for w in words:
        w_lower = w.lower()
        # Get stem via plainto_tsquery
        cur.execute("SELECT plainto_tsquery('spanish', %s)", (w,))
        stem = str(cur.fetchone()[0]).strip("'")  # Remove surrounding quotes
        
        if w_lower in or_map:
            # stem | alt1 | alt2 (without quotes on stems since they're already tsquery tokens)
            or_terms = [stem] + or_map[w_lower]
            parts.append("(" + " | ".join(or_terms) + ")")
        else:
            parts.append("'" + stem + "'")
    
    return " & ".join(parts)

# Test all benchmark queries
tests = [
    ("LIVA", "Autoliquidacion trimestral iva modelo 303", "LIVA", "123"),
    ("IRPF", "Declaracion anual irpf modelo 100", "LIRPF", "124"),
    ("IRNR", "No residente rentas inmobiliarias modelo 216", "LIRNR", "123"),
    ("LGT", "Obligaciones formales tributarias LGT", "LGT", "56"),
    ("DAC6", "Mecanismos transfronterizos DAC6", "DAC6", "1"),
]

for name, query, norma, art in tests:
    tsq = build_tsquery(query)
    print(f"\n=== {name}: {query}")
    print(f"  tsquery: {tsq}")
    
    try:
        cur.execute(f"""
            SELECT cf.search_vector @@ ({tsq}) as match_test
            FROM documento_fragmento cf
            WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo=%s) AND numero=%s)
            LIMIT 1
        """, (norma, art))
        result = cur.fetchone()[0]
        print(f"  MATCH: {result}")
    except Exception as e:
        print(f"  ERROR: {e}")
    
    cur.execute("""
        SELECT cf.search_vector FROM documento_fragmento cf
        WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo=%s) AND numero=%s)
        LIMIT 1
    """, (norma, art))
    vec = cur.fetchone()[0]
    print(f"  vector: {vec}")

conn.close()
