#!/usr/bin/env python
"""Scan worker files and generate dead-letter integration patches.

Categorizes workers by error-handling pattern and produces the
appropriate patch to wire each one into the dead-letter queue
(runtime.handle_worker_failure / dead_letter.add_dead_letter).

Usage:
    python integrate_dead_letter.py --dry-run
    python integrate_dead_letter.py --apply --all
    python integrate_dead_letter.py --dry-run --workers dac8.py prospectos.py
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

WORKERS_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "workers"


# ---------------------------------------------------------------------------
# Pattern detection
# ---------------------------------------------------------------------------

PATTERN_B_RETURN = re.compile(
    r"^\s*return\s*\{\s*['\"]success['\"]\s*:\s*False\s*,\s*['\"]error['\"]\s*:\s*str\(exc\)\s*\}",
    re.MULTILINE,
)

PATTERN_C_BOE = re.compile(
    r"from apps\.workers\.boe import run_sync|from apps\.workers import boe|from \.boe import run_sync",
)

PATTERN_E_NO_SYNC_MAIN = re.compile(
    r"def\s+run_sync\s*\(|def\s+main\s*\(",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class WorkerFile:
    path: Path
    name: str
    pattern: str
    has_logger: bool = False
    has_engine: bool = False
    has_entity_id: bool = False
    has_entity_type: bool = False


@dataclass
class PatchResult:
    worker: str
    pattern: str
    status: str
    diff: str = ""
    reason: str = ""


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

def detect_pattern(content: str, path: Path) -> str:
    """Return one of: A, B, C, D, E, SKIP."""
    name = path.name
    if name in ("__init__.py", "runtime.py", "dead_letter.py"):
        return "SKIP"

    if PATTERN_C_BOE.search(content):
        return "C"

    if not PATTERN_E_NO_SYNC_MAIN.search(content):
        return "E"

    if PATTERN_B_RETURN.search(content):
        return "B"

    if re.search(r"except\s+Exception\s+as\s+exc", content) and re.search(r"\s+raise\s*$", content, re.MULTILINE):
        return "A"

    return "D"


def needs_import_handle_worker(content: str) -> bool:
    return "handle_worker_failure" in content


def get_worker_name(content: str) -> str:
    m = re.search(r'''worker_name\s*=\s*['"]([^'"]+)['"]''', content)
    if m:
        return m.group(1)
    return ""


def get_entity_context(content: str) -> dict:
    has_entity_id = "entity_id" in content
    has_entity_type = "entity_type" in content
    has_engine = "engine = create_engine" in content or "get_engine()" in content
    has_logger = "logger = " in content or "logging.getLogger" in content
    return {
        "has_engine": has_engine,
        "has_logger": has_logger,
        "has_entity_id": has_entity_id,
        "has_entity_type": has_entity_type,
    }


# ---------------------------------------------------------------------------
# Patch generation helpers
# ---------------------------------------------------------------------------

def _find_except_block(lines, start_idx):
    """Find the except Exception as exc: line and its body up to raise or return."""
    base_indent = ""
    j = start_idx
    while j < len(lines):
        line = lines[j]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            j += 1
            continue
        base_indent = re.match(r"(\s*)", line).group(1) if re.match(r"(\s*)", line) else ""
        break

    body_lines = []
    k = start_idx + 1
    while k < len(lines):
        next_line = lines[k]
        stripped = next_line.strip()
        if stripped == "":
            body_lines.append(next_line)
            k += 1
            continue
        next_indent = re.match(r"(\s*)", next_line)
        next_indent_str = next_indent.group(1) if next_indent else ""
        if next_indent_str and len(next_indent_str) <= len(base_indent):
            break
        body_lines.append(next_line)
        if stripped in ("raise",):
            k += 1
            break
        k += 1

    return base_indent, body_lines, k


def generate_patch_a_b(content, worker_name):
    """Unified patcher for patterns A and B.

    Pattern A: replace 'raise' with dead-letter check + return
    Pattern B: insert dead-letter check before 'return {...error...}'
    """
    lines = content.splitlines(keepends=True)
    result = []
    i = 0
    patched = False

    while i < len(lines):
        line = lines[i]
        result.append(line)

        if not patched and "except Exception as exc" in line and line.strip().endswith(":"):
            base_indent, body_lines, end_idx = _find_except_block(lines, i)
            inner = base_indent + "    "

            body_text = "".join(body_lines)

            # Pattern A: has raise
            if "raise" in body_text:
                replacement_lines = []
                for bl in body_lines:
                    if bl.strip() == "raise":
                        replacement_lines.append(
                            f'{inner}if not handle_worker_failure(engine, {worker_name!r}, '
                            f'str(entity_id), "sync_entity", exc):\n'
                        )
                        replacement_lines.append(
                            f'{inner}    logger.warning("Entity %s moved to dead-letter", entity_id)\n'
                        )
                        replacement_lines.append(f"{inner}    return\n")
                    else:
                        replacement_lines.append(bl)
                result.extend(replacement_lines)
                i = end_idx
                patched = True
                continue

            # Pattern B: has return {...success: False, error:...}
            if "return" in body_text and "success" in body_text and "error" in body_text:
                before_return = []
                after_return = []
                for bl in body_lines:
                    s = bl.strip()
                    if s.startswith("return") and "'success'" in s and "'error'" in s:
                        before_return.append(
                            f'{inner}if not handle_worker_failure(engine, {worker_name!r}, '
                            f'str(entity_id), "sync_entity", exc):\n'
                        )
                        before_return.append(
                            f'{inner}    logger.warning("Entity %s moved to dead-letter", entity_id)\n'
                        )
                        after_return.append(bl)
                    else:
                        before_return.append(bl)
                result.extend(before_return)
                result.extend(after_return)
                i = end_idx
                patched = True
                continue

        i += 1

    return "".join(result)


def generate_patch_d(content, worker_name):
    """Wrap run_sync body in try/except with dead-letter."""
    lines = content.splitlines(keepends=True)
    result = []
    i = 0
    patched = False

    while i < len(lines):
        line = lines[i]
        result.append(line)

        if not patched and re.match(r"\s*def\s+run_sync\s*\(", line):
            # Find function body indentation
            j = i + 1
            body_indent = "    "
            while j < len(lines):
                bl = lines[j]
                stripped = bl.strip()
                if stripped and not stripped.startswith("#"):
                    m = re.match(r"(\s*)", bl)
                    body_indent = m.group(1) if m else body_indent
                    break
                j += 1

            # Find function end
            func_end = len(lines)
            for k in range(j, len(lines)):
                if re.match(r"\s*def\s+", lines[k]) or re.match(r"\s*if\s+__name__", lines[k]):
                    func_end = k
                    break

            # Skip docstring if present
            doc_end = j
            if j < len(lines):
                first = lines[j].strip()
                for quote in ('"""', "'''"):
                    if first.startswith(quote):
                        doc_end = j + 1
                        while doc_end < len(lines):
                            if quote in lines[doc_end]:
                                doc_end += 1
                                break
                            doc_end += 1
                        break

            inner = body_indent + "    "
            inner2 = body_indent + "    "

            # Re-add the def line with try: after docstring
            result.pop()
            result.append(line)

            # Add docstring lines
            for k in range(i + 1, doc_end):
                result.append(lines[k])

            result.append(f"{inner}try:\n")

            # Indent function body
            for k in range(doc_end, func_end):
                result.append(f"{inner}{lines[k]}")

            result.append(f"\n{inner}except Exception as exc:\n")
            result.append(f"{inner2}logger.error('Sync failed: %s', exc)\n")
            result.append(
                f'{inner2}if not handle_worker_failure(engine, {worker_name!r}, '
                f'str(entity_id), "sync_entity", exc):\n'
            )
            result.append(f'{inner2}    logger.warning("Entity %s moved to dead-letter", entity_id)\n')
            result.append(f'{inner2}    return {{"success": False, "error": str(exc)}}\n')
            result.append(f'{inner2}return {{"success": False, "error": str(exc)}}\n')

            # Copy remaining
            for k in range(func_end, len(lines)):
                result.append(lines[k])

            i = len(lines)
            patched = True
            continue

        i += 1

    return "".join(result)


def add_imports(content, new_imports):
    """Add imports after existing imports section."""
    lines = content.splitlines(keepends=True)
    result = []
    inserted = False
    import_block_end = 0

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            import_block_end = i + 1
        elif stripped == "" and import_block_end > 0:
            import_block_end = i
            break
        elif import_block_end > 0:
            break

    for i, line in enumerate(lines):
        if i == import_block_end and not inserted:
            for imp in new_imports:
                result.append(imp + "\n")
            inserted = True
        result.append(line)

    if not inserted:
        result.insert(0, "\n".join(new_imports) + "\n\n")

    return "".join(result)


# ---------------------------------------------------------------------------
# Scanning
# ---------------------------------------------------------------------------

def scan_workers(workers_dir, specific_files=None):
    """Scan worker files and categorize them by pattern."""
    workers = []
    target_files = specific_files if specific_files else sorted(workers_dir.glob("*.py"))

    for path in target_files:
        if not path.is_file():
            continue
        name = path.name
        if name in ("__init__.py", "runtime.py", "dead_letter.py"):
            continue

        content = path.read_text(encoding="utf-8")
        pattern = detect_pattern(content, path)
        if pattern == "SKIP":
            continue

        ctx = get_entity_context(content)
        workers.append(WorkerFile(
            path=path, name=name, pattern=pattern,
            has_logger=ctx["has_logger"],
            has_engine=ctx["has_engine"],
            has_entity_id=ctx["has_entity_id"],
            has_entity_type=ctx["has_entity_type"],
        ))

    return workers


def _make_diff(name, old, new):
    """Generate a unified diff string."""
    return "".join(
        difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            fromfile=f"a/apps/workers/{name}",
            tofile=f"b/apps/workers/{name}",
        )
    )


def generate_patches(workers, apply=False):
    """Generate patches for all workers in the list."""
    results = []

    for wf in workers:
        content = wf.path.read_text(encoding="utf-8")
        worker_name = get_worker_name(content) or wf.name.replace(".py", "")

        if wf.pattern == "C":
            results.append(PatchResult(wf.name, "C", "skip",
                                      reason="Wrapper worker - delegates to boe.py, no patch needed"))
            continue

        if wf.pattern == "E":
            results.append(PatchResult(wf.name, "E", "skip",
                                      reason="Utility/data module - no sync function"))
            continue

        # Patterns A, B, D all use the same generation pipeline now
        new_content = generate_patch_a_b(content, worker_name)

        # Fallback: if generate_patch_a_b didn't change anything, try generate_patch_d
        if new_content == content:
            new_content = generate_patch_d(content, worker_name)

        diff = _make_diff(wf.name, content, new_content)
        status_label = f"patch_{wf.pattern.lower()}"

        if needs_import_handle_worker(content):
            pass  # already has imports
        else:
            new_content = add_imports(new_content, ["from runtime import handle_worker_failure"])
            diff = _make_diff(wf.name, content, new_content)
            status_label = f"patch_{wf.pattern.lower()}_import"

        if apply:
            wf.path.write_text(new_content, encoding="utf-8")
            status_label = f"applied_{wf.pattern.lower()}"

        reason_map = {
            "A": "Structured exception handler - add dead-letter on failure",
            "B": "Silent fail - add dead-letter check before returning error",
            "D": "No exception handling - wrap run_sync in try/except",
        }
        results.append(PatchResult(
            wf.name, wf.pattern, status_label, diff=diff,
            reason=reason_map.get(wf.pattern, ""),
        ))

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scan workers and generate dead-letter integration patches"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Show what changes would be made without applying",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Apply the patches to files",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Process all workers (default when no --workers specified)",
    )
    parser.add_argument(
        "--workers", nargs="+", metavar="FILE",
        help="Process specific worker files (by filename)",
    )

    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("Error: specify --dry-run or --apply")
        sys.exit(1)

    if args.dry_run and args.apply:
        print("Error: --dry-run and --apply are mutually exclusive")
        sys.exit(1)

    workers_dir = WORKERS_DIR
    if not workers_dir.exists():
        print(f"Error: workers directory not found: {workers_dir}")
        sys.exit(1)

    specific_files = None
    if args.workers:
        specific_files = [workers_dir / f for f in args.workers]

    workers = scan_workers(workers_dir, specific_files)

    if not workers:
        print("No worker files to process.")
        sys.exit(0)

    print(f"Scanned {len(workers)} worker files")
    print()

    # Group by pattern
    by_pattern = {}
    for wf in workers:
        by_pattern.setdefault(wf.pattern, []).append(wf)

    for pat in sorted(by_pattern):
        files = by_pattern[pat]
        skip_reasons = {"C": "wrapper-boe", "E": "utility-data"}
        label = skip_reasons.get(pat, f"pattern-{pat}")
        print(f"  Pattern {pat} ({label}): {len(files)} files")
        for wf in files:
            print(f"    - {wf.name}")
    print()

    results = generate_patches(workers, apply=args.apply)

    # Summary counts
    counts = {}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1

    print("Summary:")
    for status in sorted(counts):
        print(f"  {status}: {counts[status]}")
    print()

    for r in results:
        if r.status.startswith("skip"):
            print(f"[SKIP] {r.worker} - {r.reason}")
        else:
            print(f"[{r.status.upper()}] {r.worker} - {r.reason}")
            if r.diff:
                print(r.diff)
                print()

    if args.apply:
        print("Patches applied successfully.")
    else:
        print("Dry run - no files modified.")


if __name__ == "__main__":
    main()
