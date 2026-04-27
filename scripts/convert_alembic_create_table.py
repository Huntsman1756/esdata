#!/usr/bin/env python3
"""
Convert all op.create_table() calls in Alembic migration files to raw SQL
CREATE TABLE IF NOT EXISTS for idempotent migrations.

This version properly handles:
- sa.Column() with name, type, and kwargs
- sa.ForeignKeyConstraint() at table level
- sa.UniqueConstraint() at table level
- sa.CheckConstraint() at table level
- sa.PrimaryKeyConstraint() at table level
- sa.Index() at table level (converted to CREATE INDEX statements)
- sa.ForeignKey() inline in Column
- Various type conversions (UUID, Numeric, ARRAY, etc.)
- server_default values with quoted strings
- Comments on columns
- autoincrement=True on primary key columns (produces SERIAL)
- default= values on columns
- postgresql_using, postgresql_where, postgresql_ops on Index
"""

import re
import sys
from pathlib import Path


def convert_type(sa_type_str):
    """Convert a SQLAlchemy type expression to PostgreSQL SQL type."""
    s = sa_type_str.strip()

    # UUID with dialect
    if 'dialects.postgresql.UUID()' in s or 'postgresql.UUID()' in s:
        return 'UUID'

    # Numeric(precision, scale)
    m = re.match(r'sa\.Numeric\((\d+),\s*(\d+)\)', s)
    if m:
        return f'NUMERIC({m.group(1)},{m.group(2)})'

    # ARRAY(sa.Text()) or ARRAY(sa.String())
    m = re.match(r'sa\.ARRAY\(sa\.Text\(\)\)', s)
    if m:
        return 'TEXT[]'
    m = re.match(r'sa\.ARRAY\(sa\.String\(\)\)', s)
    if m:
        return 'TEXT[]'

    # TIMESTAMP(timezone=True)
    if 'sa.TIMESTAMP(timezone=True)' in s or 'sa.TIMESTAMP()' in s:
        return 'TIMESTAMPTZ'

    # DateTime(timezone=True) or DateTime()
    if 'sa.DateTime' in s:
        return 'TIMESTAMPTZ'

    # Date
    if 'sa.Date()' in s:
        return 'DATE'

    # Generic types
    type_map = {
        'sa.Text()': 'TEXT',
        'sa.String()': 'TEXT',
        'sa.String(50)': 'VARCHAR(50)',
        'sa.String(100)': 'VARCHAR(100)',
        'sa.Integer()': 'INTEGER',
        'sa.Float()': 'FLOAT',
        'sa.Boolean()': 'BOOLEAN',
        'sa.JSONB': 'JSONB',
    }
    if s in type_map:
        return type_map[s]

    # sa.Text() with length
    m = re.match(r'sa\.String\((\d+)\)', s)
    if m:
        return f'VARCHAR({m.group(1)})'

    # sa.JSON()
    if 'sa.JSON()' in s:
        return 'JSONB'

    # Fallback: try to extract the base type
    m = re.match(r'sa\.(\w+)', s)
    if m:
        base = m.group(1)
        fallback = {
            'Text': 'TEXT', 'String': 'TEXT', 'Integer': 'INTEGER',
            'Float': 'FLOAT', 'Boolean': 'BOOLEAN', 'Date': 'DATE',
            'DateTime': 'TIMESTAMPTZ', 'JSON': 'JSONB', 'JSONB': 'JSONB',
            'Numeric': 'NUMERIC', 'TIMESTAMP': 'TIMESTAMPTZ',
        }
        return fallback.get(base, f'{base.upper()}')

    return s.upper()


def extract_server_default(sa_text_str):
    """Extract the raw SQL default value from sa.text('...') or sa.text(\"...\")."""
    s = sa_text_str.strip()
    m = re.match(r'sa\.text\("(.*)"\)', s)
    if m:
        return m.group(1)
    m = re.match(r"sa\.text\('(.*)'\)", s)
    if m:
        return m.group(1)
    # sa.func.now()
    if 'sa.func.now()' in s:
        return 'now()'
    return s


def convert_server_default_to_sql(sd_str):
    """Convert server_default value to SQL DEFAULT clause value."""
    s = sd_str.strip()
    # If it's already a SQL value (starts with quote, number, function, or special keyword)
    if s and (s[0] in ("'", '"') or s[0].isdigit() or s in ('true', 'false', 'null', 'now()', 'CURRENT_DATE')):
        return s
    # Handle things like 'pendiente_revision'::text — strip the ::type cast for DEFAULT
    m = re.match(r"(.+?)::\w+$", s)
    if m:
        return m.group(1)
    return s


def split_top_level(text):
    """Split text by top-level commas, respecting nested parens and strings."""
    args = []
    current = []
    depth = 0
    in_string = None
    i = 0

    while i < len(text):
        c = text[i]
        if in_string:
            current.append(c)
            if c == '\\' and i + 1 < len(text):
                current.append(text[i + 1])
                i += 2
                continue
            if c == in_string:
                in_string = None
        else:
            if c in ('"', "'"):
                in_string = c
                current.append(c)
            elif c == '(':
                depth += 1
                current.append(c)
            elif c == ')':
                depth -= 1
                current.append(c)
            elif c == ',' and depth == 0:
                args.append(''.join(current))
                current = []
            else:
                current.append(c)
        i += 1

    if current:
        args.append(''.join(current))

    return args


def extract_column_args(col_text):
    """Parse a sa.Column(...) expression into (name, type_str, kwargs_dict)."""
    s = col_text.strip()
    m = re.match(r'sa\.Column\(', s)
    if not m:
        return None

    # Balance parens
    inner_start = m.end()
    depth = 1
    i = inner_start
    in_string = None
    while i < len(s) and depth > 0:
        c = s[i]
        if in_string:
            if c == '\\' and i + 1 < len(s):
                i += 2
                continue
            if c == in_string:
                in_string = None
        else:
            if c in ('"', "'"):
                in_string = c
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
        i += 1

    inner = s[inner_start:i - 1]

    # Split by top-level comma
    parts = split_top_level(inner)

    if not parts:
        return None

    # First part is the column name (string literal)
    name = None
    name_m = re.match(r'\s*"([^"]+)"', parts[0])
    if not name_m:
        name_m = re.match(r"\s*'([^']+)'", parts[0])
    if not name_m:
        return None
    name = name_m.group(1)
    after_name = parts[0][name_m.end():].strip()

    # Second part (or remaining of first) is the type
    type_str = None
    if len(parts) > 1:
        type_str = parts[1].strip()
    else:
        # Type might be after name in the same part
        type_m = re.match(r'sa\.\w+[\(\].*', after_name)
        if type_m:
            type_str = after_name[type_m.start():]

    if not type_str:
        return None

    type_str = type_str.strip()

    # Remaining parts and keyword args from first part
    kwargs = {}

    # Check first part for kwargs
    for kw in ('nullable', 'unique', 'primary_key', 'autoincrement', 'comment', 'default'):
        kw_match = re.search(rf'{kw}\s*=\s*(True|False|(\d+)|"([^"]*)"|\'([^\']*)\')', after_name)
        if kw_match:
            val = kw_match.group(3) if kw_match.group(3) is not None else kw_match.group(4)
            if val is None:
                val = kw_match.group(1)
            kwargs[kw] = val

    # Check for server_default
    sd_match = re.search(r'server_default\s*=\s*sa\.text\("([^"]*)"\)', after_name)
    if not sd_match:
        sd_match = re.search(r"server_default\s*=\s*sa\.text\('([^']*)'\)", after_name)
    if not sd_match:
        sd_match = re.search(r'server_default\s*=\s*sa\.func\.now\(\)', after_name)
    if sd_match:
        kwargs['server_default'] = sd_match.group(1) if 'sa.text' in after_name else 'now()'

    # Check remaining parts for kwargs
    for part in parts[2:]:
        p = part.strip()
        for kw in ('nullable', 'unique', 'primary_key', 'autoincrement', 'comment', 'default'):
            kw_match = re.search(rf'{kw}\s*=\s*(True|False|(\d+)|"([^"]*)"|\'([^\']*)\')', p)
            if kw_match:
                val = kw_match.group(3) if kw_match.group(3) is not None else kw_match.group(4)
                if val is None:
                    val = kw_match.group(1)
                kwargs[kw] = val
        # server_default in remaining parts
        sd_match = re.search(r'server_default\s*=\s*sa\.text\("([^"]*)"\)', p)
        if not sd_match:
            sd_match = re.search(r"server_default\s*=\s*sa\.text\('([^']*)'\)", p)
        if sd_match:
            kwargs['server_default'] = sd_match.group(1)

    return (name, type_str, kwargs)


def convert_inline_fk(col_text):
    """Check if a column has an inline sa.ForeignKey() and return the SQL."""
    s = col_text.strip()
    m = re.search(r'sa\.ForeignKey\(\s*"([^"]+)"(?:\s*,\s*ondelete\s*=\s*"([^"]*)")?\s*\)', s)
    if m:
        ref = m.group(1)
        ondelete = m.group(2)
        sql = f'REFERENCES {ref}'
        if ondelete:
            sql += f' ON DELETE {ondelete.upper()}'
        return sql
    return None


def convert_fk_constraint(arg_text):
    """Convert sa.ForeignKeyConstraint([...], [...], ...) to SQL."""
    s = arg_text.strip()
    m = re.match(
        r'sa\.ForeignKeyConstraint\(\s*\[([^\]]+)\]\s*,\s*\[([^\]]+)\]\s*(?:,\s*ondelete\s*=\s*"([^"]*)")?\s*\)',
        s
    )
    if m:
        cols_str = m.group(1).strip()
        ref_cols_str = m.group(2).strip()
        ondelete = m.group(3)

        # Extract column names from ["col1", "col2"]
        cols = re.findall(r'"([^"]+)"', cols_str)
        ref_cols = re.findall(r'"([^"]+)"', ref_cols_str)

        if not cols or not ref_cols:
            return None

        ref_table = ref_cols[0]
        ref_col = ref_cols[1] if len(ref_cols) > 1 else 'id'

        sql = f'FOREIGN KEY ({", ".join(cols)}) REFERENCES {ref_table}({ref_col})'
        if ondelete:
            sql += f' ON DELETE {ondelete.upper()}'
        return sql
    return None


def convert_unique_constraint(arg_text):
    """Convert sa.UniqueConstraint([...], name='...') to SQL."""
    s = arg_text.strip()
    m = re.match(
        r'sa\.UniqueConstraint\(\s*([^\)]+)\)',
        s
    )
    if m:
        cols_str = m.group(1)
        cols = re.findall(r'"([^"]+)"', cols_str)
        if cols:
            return f'UNIQUE ({", ".join(cols)})'
    return None


def convert_check_constraint(arg_text):
    """Convert sa.CheckConstraint('...', name='...') to SQL."""
    s = arg_text.strip()
    m = re.match(r'sa\.CheckConstraint\(\s*"([^"]*)"', s)
    if m:
        return f'CHECK ({m.group(1)})'
    return None


def convert_pk_constraint(arg_text):
    """Convert sa.PrimaryKeyConstraint('...') to SQL."""
    s = arg_text.strip()
    m = re.match(r'sa\.PrimaryKeyConstraint\(\s*"([^"]+)"', s)
    if m:
        return f'PRIMARY KEY ({m.group(1)})'
    return None


def convert_index_to_sql(arg_text, table_name):
    """Convert sa.Index(...) to a CREATE INDEX SQL statement."""
    s = arg_text.strip()
    m = re.match(
        r'sa\.Index\(\s*"([^"]+)"\s*(?:,\s*"([^"]*)")*\s*(?:,\s*postgresql_using\s*=\s*"([^"]*)")*\s*(?:,\s*postgresql_ops\s*=\s*\{([^}]*)\})?\s*(?:,\s*postgresql_where\s*=\s*"([^"]*)")?\s*\)',
        s
    )
    if m:
        idx_name = m.group(1)
        cols_str = m.group(2) or ''
        postgresql_using = m.group(3)
        postgresql_ops = m.group(4)
        postgresql_where = m.group(5)

        # Collect all column names
        all_cols = re.findall(r'"([^"]+)"', cols_str)

        if not all_cols:
            return None

        cols_sql = ', '.join(all_cols)

        # Handle postgresql_ops for GIN trgm
        if postgresql_using == 'gin' and postgresql_ops:
            # Parse {col: "gin_trgm_ops"}
            ops_m = re.search(r'"([^"]+)":\s*"([^"]+)"', postgresql_ops)
            if ops_m:
                op_col = ops_m.group(1)
                op_name = ops_m.group(2)
                # Replace the column name with col op_name
                idx_cols = []
                for c in all_cols:
                    if c == op_col:
                        idx_cols.append(f'{c} {op_name}')
                    else:
                        idx_cols.append(c)
                cols_sql = ', '.join(idx_cols)

        using_clause = f' USING {postgresql_using}' if postgresql_using else ''
        where_clause = f' WHERE {postgresql_where}' if postgresql_where else ''

        return f'CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name}{using_clause} ({cols_sql}){where_clause}'
    return None


def extract_create_table_block(content, start_pos):
    """Extract the full op.create_table(...) block starting at start_pos.

    Returns (table_name, full_block_text, end_pos) or None.
    """
    match = re.search(r'op\.create_table\(', content[start_pos:])
    if not match:
        return None

    block_start = start_pos + match.start()
    paren_start = block_start + match.end() - 1

    # Balance parentheses
    depth = 0
    i = paren_start
    in_string = None
    while i < len(content):
        c = content[i]
        if in_string:
            if c == '\\' and i + 1 < len(content):
                i += 2
                continue
            if c == in_string:
                in_string = None
        else:
            if c in ('"', "'"):
                in_string = c
            elif c == '(':
                depth += 1
            elif c == ')':
                depth -= 1
                if depth == 0:
                    break
        i += 1

    if depth != 0:
        return None

    block_end = i + 1
    full_block = content[block_start:block_end]

    name_match = re.search(r'op\.create_table\(\s*["\']([^"\']+)["\']', full_block)
    if not name_match:
        return None

    table_name = name_match.group(1)
    return (table_name, full_block, block_end)


def convert_create_table(table_name, full_block):
    """Convert a full op.create_table(...) block to raw SQL + index SQLs."""
    # Extract inner content between outer parens
    inner_match = re.search(r'op\.create_table\(\s*(.+?)\s*\)\s*$', full_block, re.DOTALL)
    if not inner_match:
        return None

    inner_content = inner_match.group(1).strip()
    args = split_top_level(inner_content)

    columns_sql = []
    constraints_sql = []
    index_sqls = []
    has_pk = False

    for arg in args:
        arg = arg.strip()
        if not arg:
            continue

        # Check if it's a Column
        if arg.startswith('sa.Column('):
            col_info = extract_column_args(arg)
            if col_info:
                name, type_str, kwargs = col_info
                type_sql = convert_type(type_str)

                is_pk = kwargs.get('primary_key', 'False') == 'True'
                is_auto = kwargs.get('autoincrement', None) == 'True'
                nullable = kwargs.get('nullable', 'True') == 'True'
                unique = kwargs.get('unique', 'False') == 'True'
                default = kwargs.get('default', None)

                # Build column definition
                col_parts = [f'"{name}"', type_sql]

                # PK + SERIAL
                if is_pk:
                    has_pk = True
                    # Use SERIAL for INTEGER PKs
                    if type_sql == 'INTEGER' and not nullable:
                        col_parts[1] = 'SERIAL'
                    elif type_sql == 'UUID':
                        # UUID PKs don't get SERIAL, add default
                        if 'server_default' not in kwargs:
                            col_parts.append("DEFAULT gen_random_uuid()")
                    elif type_sql == 'SERIAL':
                        pass  # already serial

                # server_default
                if 'server_default' in kwargs:
                    sd_val = convert_server_default_to_sql(kwargs['server_default'])
                    col_parts.append(f'DEFAULT {sd_val}')

                # default= (runtime default, convert to SQL)
                if default is not None and 'server_default' not in kwargs:
                    col_parts.append(f'DEFAULT {default}')

                # NOT NULL
                if not nullable and not is_pk:
                    col_parts.append('NOT NULL')
                elif is_pk and not nullable:
                    # PK is implicitly NOT NULL but we can still add it
                    pass

                # Inline FK
                inline_fk = convert_inline_fk(arg)
                if inline_fk:
                    col_parts.append(inline_fk)

                # UNIQUE
                if unique and not is_pk:
                    col_parts.append('UNIQUE')

                # Comment
                if 'comment' in kwargs:
                    col_parts.append(f"COMMENT {kwargs['comment']}")

                columns_sql.append(' '.join(col_parts))
            continue

        # Table-level ForeignKeyConstraint
        if arg.startswith('sa.ForeignKeyConstraint('):
            fk_sql = convert_fk_constraint(arg)
            if fk_sql:
                constraints_sql.append(fk_sql)
            continue

        # Table-level UniqueConstraint
        if arg.startswith('sa.UniqueConstraint('):
            uc_sql = convert_unique_constraint(arg)
            if uc_sql:
                constraints_sql.append(uc_sql)
            continue

        # Table-level CheckConstraint
        if arg.startswith('sa.CheckConstraint('):
            cc_sql = convert_check_constraint(arg)
            if cc_sql:
                constraints_sql.append(cc_sql)
            continue

        # Table-level PrimaryKeyConstraint
        if arg.startswith('sa.PrimaryKeyConstraint('):
            pk_sql = convert_pk_constraint(arg)
            if pk_sql:
                has_pk = True
                constraints_sql.append(pk_sql)
            continue

        # Table-level Index
        if arg.startswith('sa.Index('):
            idx_sql = convert_index_to_sql(arg, table_name)
            if idx_sql:
                index_sqls.append(idx_sql)
            continue

    # Build the CREATE TABLE SQL
    all_parts = columns_sql + constraints_sql
    if not all_parts:
        return None, []

    columns_str = ',\n                '.join(all_parts)
    create_sql = f'CREATE TABLE IF NOT EXISTS {table_name} (\n                {columns_str}\n            )'

    return create_sql, index_sqls


def process_file(filepath):
    """Process a single migration file. Returns (modified, table_count)."""
    with open(filepath, 'r') as f:
        content = f.read()

    # Check if file has any op.create_table
    if 'op.create_table' not in content:
        return (False, 0)

    modified = False
    table_count = 0
    result = content

    # Find and replace all op.create_table(...) blocks
    pos = 0
    new_parts = []

    while pos < len(result):
        match = re.search(r'op\.create_table\(', result[pos:])
        if not match:
            new_parts.append(result[pos:])
            break

        new_parts.append(result[pos:pos + match.start()])

        block_start = pos + match.start()
        table_info = extract_create_table_block(result, block_start)

        if table_info:
            table_name, full_block, block_end = table_info
            create_sql, index_sqls = convert_create_table(table_name, full_block)
            if create_sql:
                # Replace op.create_table(...) with op.execute("CREATE TABLE IF NOT EXISTS ...")
                new_parts.append(f'    op.execute(\n        """\n        {create_sql}\n        """\n    )')
                table_count += 1
                modified = True

                # Add index SQLs as separate op.execute calls after the table
                for idx_sql in index_sqls:
                    new_parts.append(f'\n    op.execute(\n        """\n        {idx_sql}\n        """\n    )')

                pos = block_end
                continue

        # If conversion failed, keep original
        new_parts.append(full_block)
        pos = block_end

    if not modified:
        return (False, 0)

    new_content = ''.join(new_parts)

    with open(filepath, 'w') as f:
        f.write(new_content)

    return (True, table_count)


def main():
    versions_dir = Path('/Users/daniel/Documents/GitHub/esdata/alembic/versions')

    files_to_process = [
        '20260425_0006_eval_history.py',
        '20260425_0009_workflow_cases.py',
        '20260425_0010_pgc.py',
        '20260426_0015_pgc_xbrl_mapping.py',
        '20260426_0016_editorial_internal.py',
        '20260426_0017_playbooks_evidencia.py',
        '20260426_0018_micro_obligaciones.py',
        '20260426_0019_linea_criterio.py',
        '20260426_0021_risk_control_matrix.py',
        '20260426_0024_cnmv_document_versioning.py',
        '20260426_0024_cnmv_versioning.py',
        '20260426_0025_cnmv_regulation_links.py',
        '20260426_0026_cnmv_obligation_links.py',
        '20260426_0026_irs_fiscal_compliance.py',
        '20260426_0027_calendario_fiscal.py',
        '20260426_0028_irnr_worker_tables.py',
        '20260426_0029_international_obligations.py',
        '20260426_0029_irs_modelo.py',
        '20260426_0030_ai_governance_persistence.py',
        '20260427_0033_source_revision_tracking.py',
        '20260427_0034_embedding_versioning.py',
    ]

    results = []
    for fname in files_to_process:
        filepath = versions_dir / fname
        if not filepath.exists():
            print(f"SKIP: {fname} (not found)")
            continue

        modified, table_count = process_file(filepath)
        if modified:
            results.append((fname, table_count))
            print(f"MODIFIED: {fname} ({table_count} tables)")
        else:
            print(f"UNCHANGED: {fname}")

    print(f"\n{'='*60}")
    print(f"Summary: {len(results)} files modified")
    total_tables = sum(tc for _, tc in results)
    print(f"Total tables made idempotent: {total_tables}")


if __name__ == '__main__':
    main()
