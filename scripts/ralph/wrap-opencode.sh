#!/bin/sh
# Wrapper para usar opencode como herramienta de Ralph
# Lee el prompt desde stdin y lo pasa a opencode -p

if [ -z "$PATH_TO_OPENCOD" ]; then
  OPENCOD=$HOME/go/bin/opencod
else
  OPENCOD=$PATH_TO_OPENCOD
fi

# Leer todo el stdin y pasarlo a opencode
if [ -s /dev/stdin ]; then
  PROMPT=$(cat /dev/stdin)
  "$OPENCOD" -p "$PROMPT"
else
  echo "Error: empty input" >&2
  exit 1
fi
