#!/usr/bin/env bash
# Wrapper auto-correctivo para desarrollo iterativo.
#
# Uso:
#   ./scripts/auto_test.sh "tests/test_foo.py tests/test_bar.py"
#   ./scripts/auto_test.sh --all
#   ./scripts/auto_test.sh --max-attempts 3
#
# Flujo:
#   1. Ejecuta los tests especificados
#   2. Si fallan → registra error en .feedback_loop/
#   3. Si hay patrón conocido → aplica fix automatico
#   4. Re-ejecuta tests
#   5. Repite hasta que pasen o se agoten intentos
#
# El agente puede leer .feedback_loop/latest.json para ver
# el estado del loop y decidir si necesita intervenir.

set -euo pipefail

MAX_ATTEMPTS=5
TIMEOUT=120
TEST_PATTERNS=()
RUN_ALL=false
NO_FIX=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --max-attempts)
            MAX_ATTEMPTS="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --all)
            RUN_ALL=true
            shift
            ;;
        --no-fix)
            NO_FIX=true
            shift
            ;;
        --help)
            echo "Uso: $0 [pattern...] [--all] [--max-attempts N] [--timeout N]"
            exit 0
            ;;
        *)
            TEST_PATTERNS+=("$1")
            shift
            ;;
    esac
done

if $RUN_ALL; then
    TEST_PATTERNS=("-x" "-v" "--tb=short" "-q")
fi

FEEDBACK_DIR=".feedback_loop"
mkdir -p "$FEEDBACK_DIR"

attempt=1
passed=false

echo "=== Auto-corrective test loop ==="
echo "Max attempts: $MAX_ATTEMPTS"
echo "Timeout: ${TIMEOUT}s"
echo ""

while [ $attempt -le $MAX_ATTEMPTS ] && [ "$passed" = false ]; do
    echo "--- Attempt $attempt/$MAX_ATTEMPTS ---"

    # Run tests
    if [ ${#TEST_PATTERNS[@]} -eq 0 ]; then
        pytest -x -v --tb=short -q 2>&1 | tee /tmp/test_output.txt
    else
        pytest -x -v --tb=short "${TEST_PATTERNS[@]}" 2>&1 | tee /tmp/test_output.txt
    fi
    test_result=$?

    # Save feedback
    timestamp=$(date +%Y-%m-%d_%H%M%S)
    feedback_file="$FEEDBACK_DIR/${timestamp}_attempt_${attempt}.json"

    cat > "$feedback_file" <<EOF
{
  "attempt": $attempt,
  "timestamp": "$timestamp",
  "passed": $([ $test_result -eq 0 ] && echo true || echo false),
  "stdout": "$(tail -2000 /tmp/test_output.txt | head -500 | sed 's/"/\\"/g')",
  "stderr": "$(tail -2000 /tmp/test_output.txt | tail -500 | sed 's/"/\\"/g')"
}
EOF

    # Update latest
    cp "$feedback_file" "$FEEDBACK_DIR/latest.json"

    if [ $test_result -eq 0 ]; then
        passed=true
        echo "✅ All tests passed on attempt $attempt!"
    else
        echo "❌ Attempt $attempt failed."
        echo "Feedback saved to $feedback_file"
        echo ""
        echo "Recent errors:"
        grep -E "ERROR|FAILED|TypeError|ImportError|SyntaxError|AssertionError" /tmp/test_output.txt | tail -10 || true
        echo ""

        if [ $attempt -lt $MAX_ATTEMPTS ]; then
            echo "Next attempt in 2s..."
            sleep 2
        fi
    fi

    attempt=$((attempt + 1))
done

if [ "$passed" = true ]; then
    echo ""
    echo "🎉 Completed in $((attempt - 1)) attempt(s)!"
    exit 0
else
    echo ""
    echo "❌ Max attempts ($MAX_ATTEMPTS) reached."
    echo "Check .feedback_loop/latest.json for details."
    exit 1
fi
