import psycopg2

conn = psycopg2.connect("dbname=esdata user=esdata password=testpass host=localhost port=5434")
cur = conn.cursor()

# Simular el tsquery que genera _build_tsquery para "Autoliquidacion trimestral IVA modelo 303"
# Las palabras clave son: autoliquidacion, trimestral, iva, modelo, 303
# El tsquery debe ser: 'autoliquidacion' & 'trimestral' & ('iva' | 'liv') & 'model' & '303'

cur.execute("""
SELECT cf.search_vector @@ ('autoliquidacion' & 'trimestral' & ('iva' | 'liv') & 'model' & '303') as match_expanded
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
""")
print("Match con 'iva' | 'liv':", cur.fetchone()[0])

cur.execute("""
SELECT cf.search_vector @@ ('autoliquidacion' & 'trimestral' & 'iva' & 'model' & '303') as match_iva_only
FROM documento_fragmento cf
WHERE cf.documento_origen_id IN (SELECT id FROM articulo WHERE norma_id = (SELECT id FROM norma WHERE codigo='LIVA') AND numero='123')
""")
print("Match con solo 'iva':", cur.fetchone()[0])

cur.close()
conn.close()
