#!/usr/bin/env python
"""Apply dead-letter patch to workers using Python AST - correct approach."""

import ast
import os
import sys

WORKERS_DIR = r"G:\_Proyectos\esdata\apps\workers"

# Workers that need dead-letter integration
# Categorized by their pattern:

# Pattern A: structured try/except with log + raise
# These have: try: body; except: log(); raise
# → Replace raise with: if not handle_worker_failure(): return
PAT_A = [
    'aeat_models.py', 'aeat_irnr.py', 'boe.py', 'cnmv.py', 'jurisprudencia.py',
    'corporate_sustainability.py', 'dac8.py', 'dgt.py', 'teac.py', 'eurlex.py',
    'prospectos.py', 'rirnr.py', 'sepblac.py', 'sustainable_finance.py',
    'borme.py', 'aepd.py', 'bde.py', 'bdns.py', 'candoj.py',
    'csdr.py', 'dac_directives.py', 'dgt_doctrina.py', 'fraud.py',
    'ley112009_socimi.py', 'ley13_2023.py', 'ley222014_lecr.py', 'mica.py',
    'mifid_mar_dora.py'
]

# Pattern B: try/except with return error dict (no re-raise)
# These have: try: body; except: return {error: ...}
# → Add dead-letter check before return
PAT_B = [
    'aifmd_ucits.py', 'consumer_credit.py', 'consumer_credit_real.py',
    'crd_brrd_emir.py', 'csr.py', 'dac8_real.py', 'dora.py', 'giin.py',
    'insurance.py', 'mar_mifid.py', 'pbc.py', 'pgc.py', 'pgc_real.py',
    'pgc_xbrl_mapping.py', 'priips_ownership.py', 'psd2.py', 'screening.py',
    'screening_real.py', 'sfdr.py', 'solvency.py', 'xbrl.py', 'xbrl_taxonomy.py'
]

# Pattern C: wrapper workers (delegate to boe.py) - skip
PAT_C = [
    'ley112021.py', 'ley12010.py', 'ley222010.py', 'ley272014.py',
    'ley62018.py', 'nrv9.py', 'rd2172008.py', 'trlmv.py'
]

# Pattern D: utility/data only - skip
PAT_D = [
    'change_detection.py', 'embeddings.py', 'entrypoint.py', 'entity_identity.py',
    'modelos_support.py', 'pgc_dataset.py', 'vocabulary.py', 'vocabulary_validation.py'
]

# Workers with non-standard patterns (need special handling)
PAT_SPECIAL = [
    'legalize_es.py', 'micro_obligaciones.py'
]

def patch_with_import(path, patch_code):
    """Read file, insert import and patch, write back."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    
    # Add import after argparse/os imports if not present
    if 'from runtime import handle_worker_failure' not in content:
        # Find a good place for the import (after 'from runtime import ...' blocks)
        for i, line in enumerate(lines):
            if line.startswith('from runtime import '):
                # Append to existing import block
                if i + 1 < len(lines) and lines[i+1].strip().startswith('('):
                    # Multi-line import - find closing paren
                    j = i
                    while j < len(lines):
                        lines[j] += ',\n        handle_worker_failure' if not lines[j].rstrip().endswith(',') else lines[j]
                        if ')' in lines[j] and 'handle_worker_failure' not in lines[j]:
                            lines[j] = lines[j].rstrip().rstrip(',').rstrip() + ',\n        handle_worker_failure\n'
                            j += 1
                            break
                        j += 1
                    break
                elif '(' in line and ')' not in line:
                    # Single line with open paren
                    lines[i] = line.rstrip() + ',\n\n        handle_worker_failure\n'
                    break
            elif line.startswith('import ') and 'argparse' in content[:content.find(line)]:
                # Found import area, insert after it
                pass
        else:
            # No runtime import found, add one after most other imports
            for i, line in enumerate(lines):
                if line.strip().startswith('from sqlalchemy'):
                    lines.insert(i, 'from runtime import handle_worker_failure\n')
                    break
    
    # Now apply the patch code
    if patch_code:
        if 'INSERT_PATCH_HERE' in content:
            content = content.replace('INSERT_PATCH_HERE', patch_code)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def test_ast():
    """Test AST approach on a sample file"""
    test_file = os.path.join(WORKERS_DIR, 'boe.py')
    with open(test_file, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read())
    
    print(f"Parsed {test_file}: {len(tree.body)} top-level nodes")
    
    # Find the run_sync function
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == 'run_sync':
            print(f"  Found async run_sync at line {node.lineno}")
        elif isinstance(node, ast.FunctionDef) and node.name == 'run_sync':
            print(f"  Found sync run_sync at line {node.lineno}")
            # Look for try/except in this function
            for child in ast.walk(node):
                if isinstance(child, ast.Try):
                    for handler in child.handlers:
                        if isinstance(handler.type, ast.Name) and handler.type.id == 'Exception':
                            print(f"    Found except Exception at line {handler.lineno}, body len = {len(body.children)}")
                            for stmt in handler.body[:3]:
                                print(f"      {ast.dump(stmt)[:100]}")

if __name__ == '__main__':
    dry_run = '--dry-run' in sys.argv
    apply = '--apply' in sys.argv
    
    print(f"Dead-letter patcher {'(DRY RUN)' if dry_run else ''}")
    print(f"Pattern A: {len(PAT_A)} workers")
    print(f"Pattern B: {len(PAT_B)} workers")
    print(f"Skip Pattern C: {len(PAT_C)} workers (boe wrappers)")
    print(f"Skip Pattern D: {len(PAT_D)} workers (utility)")
    print(f"Special: {len(PAT_SPECIAL)} workers")
    
    if dry_run or apply:
        test_ast()
    else:
        print("Use --dry-run to see planned changes, --apply to make them")
