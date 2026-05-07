#!/usr/bin/env python
"""Dead-letter patcher using AST for correct import insertion."""

import ast
import os
import sys

WORKERS_DIR = r"G:\_Proyectos\esdata\apps\workers"

# Workers that need dead-letter (skip boe.py, aeat_irnr.py, modelos.py as they need different handling)
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

def fix_imports(tree, lines):
    """Insert handle_worker_failure import using AST."""
    content = ast.unparse(tree)
    if 'handle_worker_failure' in content:
        return lines
    
    # Find first 'from runtime import' block and append
    for i, line in enumerate(lines):
        if line.startswith('from runtime import '):
            if '(' in line and ')' not in line:
                # Multi-line import - find closing
                j = i
                while j < len(lines):
                    if ')' in lines[j]:
                        # Insert before closing paren
                        lines[j] = lines[j].replace(')', ',\n        handle_worker_failure\n    )')
                        break
                    j += 1
                return lines
            elif '(' not in line and ')' not in line:
                # Single line import
                lines[i] = line.rstrip() + ',\n    handle_worker_failure\n'
                return lines
    
    # No runtime import found - insert after first non-docstring line
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('from ') and 'sqlalchemy' in stripped:
            lines.insert(i, 'from runtime import handle_worker_failure\n')
            return lines
    
    return lines

def patch_except_raise(lines, worker_name):
    """Pattern A: Replace 'raise' in except block with dead-letter check."""
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped.startswith('except Exception as exc:'):
            except_indent = len(line) - len(line.lstrip())
            new_lines.append(line)
            i += 1
            
            # Copy lines until we find bare 'raise'
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
                    break
                else:
                    new_lines.append(next_line)
                    i += 1
            continue
        
        new_lines.append(line)
        i += 1
    
    return new_lines

def patch_except_return(lines, worker_name):
    """Pattern B: Insert dead-letter check before return error dict."""
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped.startswith('except Exception as exc:'):
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
                    break
                else:
                    new_lines.append(next_line)
                    i += 1
            continue
        
        new_lines.append(line)
        i += 1
    
    return new_lines

def main():
    dry_run = '--dry-run' in sys.argv
    apply = '--apply' in sys.argv
    
    if not dry_run and not apply:
        print("Usage: python fix_dead_letter.py --dry-run [--apply]")
        sys.exit(1)
    
    total = 0
    applied = 0
    
    for f in PAT_A + PAT_B:
        path = os.path.join(WORKERS_DIR, f)
        if not os.path.exists(path):
            continue
        
        with open(path, 'r', encoding='utf-8') as fh:
            content = fh.read()
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            print(f"  SKIP (parse error): {f}")
            continue
        
        lines = content.split('\n')
        lines = fix_imports(tree, lines)
        
        if f in PAT_A:
            new_lines = patch_except_raise(lines, f.replace('.py', ''))
        else:
            new_lines = patch_except_return(lines, f.replace('.py', ''))
        
        new_content = '\n'.join(new_lines)
        
        if new_content != content:
            total += 1
            if apply:
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.write(new_content)
                applied += 1
                print(f"  PATCHED: {f}")
            else:
                print(f"  WOULD PATCH: {f}")
    
    print(f"\nTotal: {total} workers, Applied: {applied}")
    if not apply:
        print("Add --apply to make changes")

if __name__ == '__main__':
    main()
