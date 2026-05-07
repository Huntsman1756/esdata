#!/usr/bin/env python
"""Safe dead-letter patcher - only inserts handle_worker_failure into runtime imports."""

import os
import sys

WORKERS_DIR = r"G:\_Proyectos\esdata\apps\workers"

PAT_A = [
    'aeat_models.py', 'cnmv.py', 'jurisprudencia.py', 'corporate_sustainability.py',
    'dac8.py', 'dgt.py', 'teac.py', 'eurlex.py', 'prospectos.py', 'rirnr.py',
    'sepblac.py', 'sustainable_finance.py', 'borme.py', 'aepd.py', 'bde.py',
    'bdns.py', 'cendoj.py', 'csdr.py', 'dac_directives.py', 'dgt_doctrina.py',
    'fraud.py', 'ley112009_socimi.py', 'ley13_2023.py', 'ley222014_lecr.py',
    'mica.py', 'mifid_mar_dora.py'
]

PAT_B = [
    'aifmd_ucits.py', 'consumer_credit.py', 'consumer_credit_real.py',
    'crd_brrd_emir.py', 'csr.py', 'dac8_real.py', 'dora.py', 'giin.py',
    'insurance.py', 'mar_mifid.py', 'pbc.py', 'pgc.py', 'pgc_real.py',
    'pgc_xbrl_mapping.py', 'priips_ownership.py', 'psd2.py', 'screening.py',
    'screening_real.py', 'sfdr.py', 'solvency.py', 'xbrl.py', 'xbrl_taxonomy.py'
]

def fix_import(lines, worker_name):
    """Insert handle_worker_failure into from runtime import block."""
    found = False
    new_lines = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped.startswith('from runtime import '):
            # This is a runtime import block
            if '(' in line and ')' in line:
                # Single line: from runtime import (a, b)
                # Insert before closing paren
                new_line = line.rstrip().rstrip(')').rstrip(',').rstrip()
                new_line += ',\n    handle_worker_failure,\n)'
                new_lines.append(new_line)
                found = True
                i += 1
                continue
            elif '(' in line and ')' not in line:
                # Multi-line import: from runtime import (
                new_lines.append(line)
                i += 1
                # Find closing paren
                while i < len(lines):
                    cline = lines[i]
                    if ')' in cline:
                        # Insert handle_worker_failure before closing paren
                        indent = ' ' * 4
                        new_lines.append(f'{indent}    handle_worker_failure,\n')
                        i += 1
                        found = True
                        break
                    else:
                        new_lines.append(cline)
                        i += 1
                continue
            else:
                # Single line: from runtime import a, b
                new_line = line.rstrip() + ',\n    handle_worker_failure\n'
                new_lines.append(new_line)
                found = True
                i += 1
                continue
        
        new_lines.append(line)
        i += 1
    
    return new_lines, found

def patch_except_raise(lines, worker_name):
    """Replace bare 'raise' in except block with dead-letter check."""
    new_lines = []
    i = 0
    found = False
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped == 'except Exception as exc:':
            except_indent = len(line) - len(line.lstrip())
            new_lines.append(line)
            i += 1
            
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()
                next_indent = len(next_line) - len(next_line.lstrip())
                
                if next_indent <= except_indent and next_stripped:
                    break
                
                if next_stripped == 'raise':
                    dl_indent = ' ' * (except_indent + 4)
                    new_lines.append(f'{dl_indent}if not handle_worker_failure(engine, \'{worker_name}\', str(entity_id), "sync_entity", exc):\n')
                    new_lines.append(f'{dl_indent}    logger.warning("Entity %s moved to dead-letter", entity_id)\n')
                    new_lines.append(f'{dl_indent}    return\n')
                    i += 1
                    found = True
                    break
                else:
                    new_lines.append(next_line)
                    i += 1
            continue
        
        new_lines.append(line)
        i += 1
    
    return new_lines, found

def patch_except_return(lines, worker_name):
    """Insert dead-letter check before return error dict in except block."""
    new_lines = []
    i = 0
    found = False
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped == 'except Exception as exc:':
            except_indent = len(line) - len(line.lstrip())
            new_lines.append(line)
            i += 1
            
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()
                next_indent = len(next_line) - len(next_line.lstrip())
                
                if next_indent <= except_indent and next_stripped:
                    break
                
                if next_stripped.startswith('return {') and '"error"' in next_stripped:
                    dl_indent = ' ' * (except_indent + 4)
                    new_lines.append(f'{dl_indent}if not handle_worker_failure(engine, \'{worker_name}\', str(entity_id), "sync_entity", exc):\n')
                    new_lines.append(f'{dl_indent}    logger.warning("Entity %s moved to dead-letter", entity_id)\n')
                    new_lines.append(next_line)
                    i += 1
                    found = True
                    break
                else:
                    new_lines.append(next_line)
                    i += 1
            continue
        
        new_lines.append(line)
        i += 1
    
    return new_lines, found

def main():
    dry_run = '--dry-run' in sys.argv
    apply = '--apply' in sys.argv
    
    if not dry_run and not apply:
        print("Usage: python fix_dead_letter_safe.py --dry-run [--apply]")
        sys.exit(1)
    
    total = 0
    applied = 0
    errors = []
    
    for f in PAT_A + PAT_B:
        path = os.path.join(WORKERS_DIR, f)
        if not os.path.exists(path):
            errors.append(f"  MISSING: {f}")
            continue
        
        with open(path, 'rb') as fh:
            content = fh.read()
        text = content.decode('utf-8')
        lines = text.split('\n')
        
        # Fix imports
        lines, import_added = fix_import(lines, f.replace('.py', ''))
        
        # Apply patch
        if f in PAT_A:
            new_lines, patch_found = patch_except_raise(lines, f.replace('.py', ''))
        else:
            new_lines, patch_found = patch_except_return(lines, f.replace('.py', ''))
        
        if not patch_found:
            errors.append(f"  NO PATCH MATCH: {f}")
            continue
        
        new_text = '\n'.join(new_lines)
        
        if new_text != text:
            total += 1
            if apply:
                with open(path, 'wb') as fh:
                    fh.write(new_text.encode('utf-8'))
                applied += 1
                print(f"  PATCHED: {f}")
            else:
                print(f"  WOULD PATCH: {f}")
    
    print(f"\nTotal: {total} workers, Applied: {applied}")
    if errors:
        print("\nErrors:")
        for e in errors:
            print(e)
    if not apply:
        print("\nAdd --apply to make changes")

if __name__ == '__main__':
    main()
