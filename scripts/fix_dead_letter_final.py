#!/usr/bin/env python
"""Dead-letter patcher - safe approach that only patches specific lines."""

import os
import sys

WORKERS_DIR = r"G:\_Proyectos\esdata\apps\workers"

# Pattern A: except block with log + raise -> replace raise with dead-letter
PAT_A = [
    'aeat_models.py', 'cnmv.py', 'jurisprudencia.py', 'corporate_sustainability.py',
    'dac8.py', 'dgt.py', 'teac.py', 'eurlex.py', 'prospectos.py', 'rirnr.py',
    'sepblac.py', 'sustainable_finance.py', 'borme.py', 'aepd.py', 'bde.py',
    'bdns.py', 'cendoj.py', 'csdr.py', 'dac_directives.py', 'dgt_doctrina.py',
    'fraud.py', 'ley112009_socimi.py', 'ley13_2023.py', 'ley222014_lecr.py',
    'mica.py', 'mifid_mar_dora.py'
]

# Pattern B: except block with return error dict -> insert dead-letter before return
PAT_B = [
    'aifmd_ucits.py', 'consumer_credit.py', 'consumer_credit_real.py',
    'crd_brrd_emir.py', 'csr.py', 'dac8_real.py', 'dora.py', 'giin.py',
    'insurance.py', 'mar_mifid.py', 'pbc.py', 'pgc.py', 'pgc_real.py',
    'pgc_xbrl_mapping.py', 'priips_ownership.py', 'psd2.py', 'screening.py',
    'screening_real.py', 'sfdr.py', 'solvency.py', 'xbrl.py', 'xbrl_taxonomy.py'
]

def find_and_patch_raise(lines, worker_name):
    """Find bare 'raise' in except Exception block and replace with dead-letter check."""
    new_lines = []
    i = 0
    found = False
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Find except Exception as exc:
        if stripped == 'except Exception as exc:':
            except_indent = len(line) - len(line.lstrip())
            new_lines.append(line)
            i += 1
            
            # Copy lines until we find bare raise at correct indent
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()
                next_indent = len(next_line) - len(next_line.lstrip())
                
                # If we hit another def/class or indent <= except, we left the block
                if next_indent <= except_indent and next_stripped and not next_stripped.startswith('#'):
                    break
                
                # Check if this is a bare 'raise' (not raise from)
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

def find_and_patch_return(lines, worker_name):
    """Find return error dict in except block and insert dead-letter before it."""
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
                
                # Check for return dict with error
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

def ensure_import(lines, worker_name):
    """Add handle_worker_failure import if not present."""
    content = '\n'.join(lines)
    if 'handle_worker_failure' in content:
        return lines, False
    
    # Find the import block to add to
    for i, line in enumerate(lines):
        if line.startswith('from runtime import '):
            # Check if it's a multi-line import
            if '(' in line and ')' not in line:
                # Multi-line - find closing paren and insert before it
                j = i
                while j < len(lines):
                    if ')' in lines[j]:
                        # Insert before the closing paren line
                        indent = ' ' * 4
                        lines.insert(j, f'{indent}    handle_worker_failure,\n')
                        return lines, True
                    j += 1
            elif '(' not in line and ')' not in line:
                # Single line import like: from runtime import X
                lines[i] = line.rstrip() + ',\n    handle_worker_failure\n'
                return lines, True
            elif '(' not in line and ')' in line:
                # Single line multi-import: from runtime import (X, Y)
                lines[i] = line.rstrip().rstrip(')').rstrip(',') + ',\n    handle_worker_failure,\n)'
                return lines, True
    
    # No runtime import found - add after first sqlalchemy import
    for i, line in enumerate(lines):
        if 'from sqlalchemy' in line:
            lines.insert(i, 'from runtime import handle_worker_failure\n')
            return lines, True
    
    # Fallback: add at top of imports
    for i, line in enumerate(lines):
        if line.startswith('import argparse') or line.startswith('import os') or line.startswith('import re'):
            lines.insert(i, 'from runtime import handle_worker_failure\n')
            return lines, True
    
    return lines, False

def main():
    dry_run = '--dry-run' in sys.argv
    apply = '--apply' in sys.argv
    
    if not dry_run and not apply:
        print("Usage: python fix_dead_letter_final.py --dry-run [--apply]")
        sys.exit(1)
    
    total = 0
    applied = 0
    errors = []
    
    for f in PAT_A + PAT_B:
        path = os.path.join(WORKERS_DIR, f)
        if not os.path.exists(path):
            print(f"  SKIP (missing): {f}")
            continue
        
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        
        lines = content.split('\n')
        
        # Ensure import
        lines, import_added = ensure_import(lines, f.replace('.py', ''))
        
        # Apply patch
        if f in PAT_A:
            new_lines, found = find_and_patch_raise(lines, f.replace('.py', ''))
        else:
            new_lines, found = find_and_patch_return(lines, f.replace('.py', ''))
        
        if not found:
            errors.append(f"  NO MATCH: {f}")
            continue
        
        new_content = '\n'.join(new_lines)
        
        if new_content != content:
            total += 1
            if apply:
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(new_content)
                applied += 1
                status = "PATCHED"
                if import_added:
                    status += " + import"
                print(f"  {status}: {f}")
            else:
                print(f"  WOULD PATCH: {f}")
        else:
            errors.append(f"  NO CHANGE: {f}")
    
    print(f"\nTotal: {total} workers, Applied: {applied}")
    if errors:
        print("\nIssues:")
        for e in errors:
            print(e)
    if not apply:
        print("\nAdd --apply to make changes")

if __name__ == '__main__':
    main()
