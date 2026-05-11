"""Verify all Python files parse cleanly."""
import os, ast, sys

errors = []

dirs = [
    ('apps/workers', 'WORKERS'),
    ('apps/api/services', 'SERVICES'),
    ('apps/api/routers', 'ROUTERS'),
    ('apps/api/middleware', 'MIDDLEWARE'),
]

for dir_path, label in dirs:
    if not os.path.exists(dir_path):
        print(f'{label}: dir not found')
        continue
    files = [f for f in os.listdir(dir_path) if f.endswith('.py') and not f.startswith('__')]
    for f in sorted(files):
        path = os.path.join(dir_path, f)
        try:
            with open(path, encoding='utf-8', errors='replace') as fh:
                ast.parse(fh.read())
        except SyntaxError as e:
            errors.append(f'{label}/{f}: line {e.lineno} - {e.msg}')
        except Exception as e:
            errors.append(f'{label}/{f}: {type(e).__name__}: {e}')

total = sum(len([f for f in os.listdir(d) if f.endswith('.py') and not f.startswith('__')]) for d, _ in dirs)
print(f'Total files checked: {total}')
print(f'Errors: {len(errors)}')
for e in errors:
    print(f'  FAIL: {e}')
if not errors:
    print('ALL FILES PASS')
