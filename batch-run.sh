#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

# Settings: edit these if you want a different sweep.
GPU=0
START_PERCENT=60
STEP=10

for cmd in nvidia-smi awk jq curl zip sudo; do
    command -v "$cmd" >/dev/null || { echo "ERROR: Missing command: $cmd" >&2; exit 1; }
done
[[ -f teapot_api.json ]] || { echo 'ERROR: Missing teapot_api.json' >&2; exit 1; }
[[ "$START_PERCENT" =~ ^[0-9]+$ && "$STEP" =~ ^[0-9]+$ ]] || { echo 'ERROR: START_PERCENT and STEP must be integers' >&2; exit 1; }
(( START_PERCENT >= 1 && START_PERCENT <= 100 && STEP > 0 )) || { echo 'ERROR: Invalid START_PERCENT or STEP' >&2; exit 1; }

GPU_NAME=$(nvidia-smi -i "$GPU" --query-gpu=name --format=csv,noheader)
LIMITS=$(nvidia-smi -i "$GPU" --query-gpu=power.min_limit,power.max_limit --format=csv,noheader,nounits)
IFS=, read -r RAW_MIN RAW_MAX <<< "$LIMITS"
# Round within the supported range, even if the driver reports fractional watts.
GPU_MIN=$(LC_ALL=C awk -v n="$RAW_MIN" 'BEGIN {if (n+0 <= 0) exit 1; printf "%.0f", int(n+0) + ((n+0)>int(n+0))}')
GPU_MAX=$(LC_ALL=C awk -v n="$RAW_MAX" 'BEGIN {if (n+0 <= 0) exit 1; printf "%.0f", int(n+0)}')
(( GPU_MIN <= GPU_MAX )) || { echo 'ERROR: Invalid GPU power limits' >&2; exit 1; }

START_WATT=$(( (GPU_MAX * START_PERCENT + 100 * STEP - 1) / (100 * STEP) * STEP ))
(( START_WATT < GPU_MIN )) && START_WATT=$GPU_MIN
(( START_WATT > GPU_MAX )) && START_WATT=$GPU_MAX

printf 'GPU %s: %s\nSupported range: %s-%s W\nBenchmark range: %s-%s W (step %s W)\n' \
    "$GPU" "$GPU_NAME" "$GPU_MIN" "$GPU_MAX" "$START_WATT" "$GPU_MAX" "$STEP"

# Every batch starts fresh. The archived ZIP files from previous runs are preserved.
rm -rf -- ./output
mkdir -p ./output
printf 'power_limit_w,seconds,image\n' > ./output/results.csv

for ((WATT=START_WATT; WATT<=GPU_MAX; WATT+=STEP)); do
    echo "=== Testing ${WATT} W ==="
    ./gpu-load-lock.sh -limit "$WATT" -command ./teapot.sh "$WATT"
done
# Always include the card's maximum, even when it is off the 10 W grid.
if (( (GPU_MAX - START_WATT) % STEP != 0 )); then
    echo "=== Testing ${GPU_MAX} W ==="
    ./gpu-load-lock.sh -limit "$GPU_MAX" -command ./teapot.sh "$GPU_MAX"
fi

zip -qr "results-$(date +%Y%m%d_%H%M%S).zip" output
echo '=== All tests completed ==='
