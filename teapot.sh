#!/usr/bin/env bash
set -euo pipefail

WATT="${1:?Usage: teapot.sh WATTS}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW="$SCRIPT_DIR/teapot_api.json"
OUT="$SCRIPT_DIR/output"
API="http://127.0.0.1:8188"

[[ -f "$WORKFLOW" ]] || { echo "Mangler API-workflow: $WORKFLOW" >&2; exit 1; }
command -v jq >/dev/null || { echo 'Mangler jq' >&2; exit 1; }
mkdir -p "$OUT"

TMP=$(mktemp "$SCRIPT_DIR/.workflow.XXXXXX")
trap 'rm -f "$TMP"' EXIT

# Ny seed for hver kørsel, så ComfyUI ikke genbruger et cachet resultat.
SEED=$(od -An -N6 -tu8 /dev/urandom | tr -d ' ')
jq --argjson seed "$SEED" '
  with_entries(if .value.class_type == "KSampler"
    then .value.inputs.seed = $seed else . end)
' "$WORKFLOW" > "$TMP"

START=$(date +%s%N)
ID=$(jq -n --slurpfile workflow "$TMP" '{prompt: $workflow[0]}' |
     curl -fsS "$API/prompt" -H 'Content-Type: application/json' --data-binary @- |
     jq -er '.prompt_id')

for ((i=0; i<1200; i++)); do
    HISTORY=$(curl -fsS "$API/history/$ID")
    STATE=$(jq -r --arg id "$ID" '.[$id].status.status_str // "pending"' <<< "$HISTORY")
    [[ "$STATE" == "error" ]] && { echo "ComfyUI fejl for $ID" >&2; exit 1; }
    [[ "$STATE" == "success" ]] && break
    sleep 0.5
done
[[ "$STATE" == "success" ]] || { echo 'Timeout fra ComfyUI' >&2; exit 1; }
ELAPSED=$(LC_ALL=C awk -v a="$START" -v b="$(date +%s%N)" 'BEGIN {printf "%.3f", (b-a)/1e9}')

IMAGE=$(jq -cer --arg id "$ID" '[.[$id].outputs[]?.images[]?][0]' <<< "$HISTORY") || {
    echo 'ComfyUI returnerede intet billede' >&2; exit 1;
}
NAME="teapot_${WATT}W_$(date +%Y%m%d_%H%M%S).png"
QUERY=$(jq -rn --argjson image "$IMAGE" '
  ($image.filename|@uri) + "&subfolder=" + ($image.subfolder // ""|@uri) +
  "&type=" + ($image.type // "output"|@uri)
')
curl -fsS "$API/view?filename=$QUERY" -o "$OUT/$NAME"
printf '%s W | %s sek. | %s\n' "$WATT" "$ELAPSED" "$OUT/$NAME"
printf '%s,%s,%s\n' "$WATT" "$ELAPSED" "$NAME" >> "$OUT/results.csv"
