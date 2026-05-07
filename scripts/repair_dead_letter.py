# Repair all 24 broken dead-letter patched workers
import os, sys

workers_dir = r'G:\_Proyectos\esdata\apps\workers'
broken_files = [
    'aeat_irnr.py', 'aeat_models.py', 'aifmd_ucits.py', 'boe.py',
    'consumer_credit_real.py', 'crd_brrd_emir.py', 'csr.py', 'dac8_real.py',
    'dora.py', 'giin.py', 'insurance.py', 'jurisprudencia.py', 'legalize_es.py',
    'mar_mifid.py', 'modelos.py', 'pbc.py', 'pgc.py', 'pgc_real.py',
    'pgc_xbrl_mapping.py', 'priips_ownership.py', 'screening_real.py', 'sfdr.py',
    'solvency.py', 'xbrl.py'
]

for f in broken_files:
    path = os.path.join(workers_dir, f)
    with open(path, 'r', encoding='utf-8') as fh:
        content = fh.read()
    
    original = content
    
    # Remove broken dead-letter imports
    content = content.replace('\nfrom runtime import handle_worker_failure\n', '\n')
    
    # Remove broken dead-letter except block (unindented body)
    lines = content.split('\n')
    new_lines = []
    skip_dead_letter = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Detect dead-letter block start
        if stripped == 'except Exception as exc:' and i + 5 < len(lines):
            next1 = lines[i+1].strip() if i+1 < len(lines) else ''
            next2 = lines[i+2].strip() if i+2 < len(lines) else ''
            if 'Sync failed' in next1 and 'handle_worker_failure' in next2:
                skip_dead_letter = True
                continue
        
        if skip_dead_letter:
            if stripped.startswith("logger.error('Sync failed"):
                continue
            if stripped.startswith('if not handle_worker_failure('):
                continue
            if stripped.startswith('logger.warning(') and 'dead-letter' in stripped:
                continue
            if stripped.startswith('return {"success": False') or stripped.startswith("return {'success': False"):
                continue
            if stripped == '' and i+1 < len(lines) and lines[i+1].strip().startswith('def '):
                skip_dead_letter = False
                new_lines.append(line)
                continue
            if stripped and (stripped.startswith('def ') or stripped.startswith('class ') or stripped.startswith('@')):
                skip_dead_letter = False
                new_lines.append(line)
                continue
            continue
        
        new_lines.append(line)
    
    content = '\n'.join(new_lines)
    content = content.replace('\n\n\n', '\n\n')
    
    if content != original:
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        print(f'Repaired: {f}')
    else:
        print(f'No changes: {f}')

print('Repair complete')
