#!/usr/bin/env python
"""Apply dead-letter patch to workers using AST - correct approach."""

import ast
import os
import sys

WORKERS_DIR = r"G:\_Proyectos\esdata\apps\workers"

# Pattern A: try/except with log + raise → replace raise with dead-letter check
PAT_A = [
    'aeat_models.py', 'aeat_irnr.py', 'boe.py', 'cnmv.py', 'jurisprudencia.py',
    'corporate_sustainability.py', 'dac8.py', 'dgt.py', 'teac.py', 'eurlex.py',
    'prospectos.py', 'rirnr.py', 'sepblac.py', 'sustainable_finance.py',
    'borme.py', 'aepd.py', 'bde.py', 'bdns.py', 'cendoj.py',
    'csdr.py', 'dac_directives.py', 'dgt_doctrina.py', 'fraud.py',
    'ley112009_socimi.py', 'ley13_2023.py', 'ley222014_lecr.py', 'mica.py',
    'mifid_mar_dora.py'
]

# Pattern B: try/except with return error dict → insert dead-letter before return
PAT_B = [
    'aifmd_ucits.py', 'consumer_credit.py', 'consumer_credit_real.py',
    'crd_brrd_emir.py', 'csr.py', 'dac8_real.py', 'dora.py', 'giin.py',
    'insurance.py', 'mar_mifid.py', 'pbc.py', 'pgc.py', 'pgc_real.py',
    'pgc_xbrl_mapping.py', 'priips_ownership.py', 'psd2.py', 'screening.py',
    'screening_real.py', 'sfdr.py', 'solvency.py', 'xbrl.py', 'xbrl_taxonomy.py'
]

# Skip these
PAT_SKIP = [
    'ley112021.py', 'ley12010.py', 'ley222010.py', 'ley272014.py',
    'ley62018.py', 'nrv9.py', 'rd2172008.py', 'trlmv.py',
    'change_detection.py', 'embeddings.py', 'entrypoint.py', 'entity_identity.py',
    'modelos_support.py', 'pgc_dataset.py', 'vocabulary.py', 'vocabulary_validation.py',
    'legalize_es.py', 'micro_obligaciones.py'
]

def add_import_if_missing(tree, lines):
    """Add from runtime import handle_worker_failure if not present."""
    content = '\n'.join(lines)
    if 'handle_worker_failure' in content:
        return lines
    
    # Find a good place for the import
    for i, line in enumerate(lines):
        if line.startswith('from runtime import '):
            # Append to existing import
            if '(' in line and ')' not in line:
                # Multi-line import starting
                j = i
                while j < len(lines):
                    lines[j] = lines[j].rstrip() + ',\n        handle_worker_failure\n'
                    if ')' in lines[j]:
                        break
                    j += 1
                return lines
            elif '(' not in line and ')' not in line:
                lines[i] = line.rstrip() + ',\n        handle_worker_failure\n'
                return lines
        elif line.startswith('import argparse') or line.startswith('import os'):
            # Insert after first import block
            for j in range(i, min(i+10, len(lines))):
                if lines[j].startswith('from ') and 'sqlalchemy' in lines[j]:
                    lines.insert(j, 'from runtime import handle_worker_failure\n')
                    return lines
    return lines

def patch_pattern_a(lines, worker_name):
    """Pattern A: Replace 'raise' after dead-letter logging with dead-letter check."""
    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        # Look for the pattern: except Exception as exc: ... log_sync ... raise
        if stripped.startswith('except Exception as exc:'):
            # Collect the except block
            except_indent = len(line) - len(line.lstrip())
            new_lines.append(line)
            i += 1
            # Copy lines until we find 'raise' or next def/class
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()
                next_indent = len(next_line) - len(next_line.lstrip())
                
                if next_indent <= except_indent and next_stripped and not next_stripped.startswith('#'):
                    # We've left the except block
                    break
                
                if next_stripped == 'raise':
                    # Replace raise with dead-letter check
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

def patch_pattern_b(lines, worker_name):
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
                
                if next_indent <= except_indent and next_stripped and not next_stripped.startswith('#'):
                    break
                
                # Look for return dict with error
                if next_stripped.startswith('return {') and '"error"' in next_stripped:
                    dl_indent = ' ' * (except_indent + 4)
                    # Insert dead-letter check before return
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
    
    # Pattern A workers
    for f in PAT_A:
        path = os.path.join(WORKERS_DIR, f)
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()
        
        # Add import
        lines = add_import_if_missing(ast.parse(''.join(lines)), lines)
        
        # Apply patch
        new_lines = patch_pattern_a(lines, f.replace('.py', ''))
        
        if new_lines != lines:
            total += 1
            if apply:
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.writelines(new_lines)
                applied += 1
                print(f"  PATCHED: {f}")
            else:
                print(f"  WOULD PATCH: {f}")
    
    # Pattern B workers
    for f in PAT_B:
        path = os.path.join(WORKERS_DIR, f)
        if not os.path.exists(path):
            continue
        with open(path, 'r', encoding='utf-8') as fh:
            lines = fh.readlines()
        
        # Add import
        lines = add_import_if_missing(ast.parse(''.join(lines)), lines)
        
        # Apply patch
        new_lines = patch_pattern_b(lines, f.replace('.py', ''))
        
        if new_lines != lines:
            total += 1
            if apply:
                with open(path, 'w', encoding='utf-8') as fh:
                    fh.writelines(new_lines)
                applied += 1
                print(f"  PATCHED: {f}")
            else:
                print(f"  WOULD PATCH: {f}")
    
    print(f"\nTotal: {total} workers, Applied: {applied}")
    if not apply:
        print("Add --apply to make changes")

if __name__ == '__main__':
    main()
