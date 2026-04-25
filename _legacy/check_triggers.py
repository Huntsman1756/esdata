import psycopg2

conn = psycopg2.connect('postgresql://esdata:testpass@localhost:5434/esdata')
cur = conn.cursor()

# Check triggers on version_articulo
print("=== Triggers on version_articulo ===")
cur.execute("""
    SELECT trigger_name, event_manipulation, action_timing, action_statement
    FROM information_schema.triggers
    WHERE event_object_table = 'version_articulo'
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0]}: {row[1]} {row[2]} -> {row[3][:200]}")
else:
    print("  No triggers found")

# Check triggers on articulo
print("\n=== Triggers on articulo ===")
cur.execute("""
    SELECT trigger_name, event_manipulation, action_timing, action_statement
    FROM information_schema.triggers
    WHERE event_object_table = 'articulo'
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0]}: {row[1]} {row[2]} -> {row[3][:200]}")
else:
    print("  No triggers found")

# Check triggers on documento_fragmento
print("\n=== Triggers on documento_fragmento ===")
cur.execute("""
    SELECT trigger_name, event_manipulation, action_timing, action_statement
    FROM information_schema.triggers
    WHERE event_object_table = 'documento_fragmento'
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0]}: {row[1]} {row[2]} -> {row[3][:200]}")
else:
    print("  No triggers found")

# Check all functions that might generate search_vector
print("\n=== Functions with search_vector ===")
cur.execute("""
    SELECT routine_name, routine_definition
    FROM information_schema.routines
    WHERE routine_schema = 'public'
      AND routine_definition LIKE '%search_vector%'
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0]}: {row[1][:300]}")
else:
    print("  No functions found")

# Check all triggers (not just info_schema)
print("\n=== All triggers ===")
cur.execute("""
    SELECT tgname, tgrelid::regclass, tgenabled, pg_get_triggerdef(oid)
    FROM pg_trigger
    WHERE tgrelid::regclass::text IN ('version_articulo', 'articulo', 'documento_fragmento')
      AND NOT tgisinternal
""")
rows = cur.fetchall()
if rows:
    for row in rows:
        print(f"  {row[0]} on {row[1]} (enabled={row[2]}): {row[3][:300]}")
else:
    print("  No triggers found")

conn.close()
