#!/usr/bin/env bash
set -euo pipefail

GPU=0
LIMIT=""
COMMAND=()

usage() {
    echo "Usage: $0 -limit WATTS -command COMMAND [ARGS...]" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        -limit)
            [[ $# -ge 2 ]] || usage
            LIMIT="$2"
            shift 2
            ;;
        -command)
            shift
            COMMAND=("$@")
            break
            ;;
        *) usage ;;
    esac
done

[[ "$LIMIT" =~ ^[0-9]+$ ]] || usage
[[ ${#COMMAND[@]} -gt 0 ]] || usage

OLD_LIMIT=$(nvidia-smi -i "$GPU" \
    --query-gpu=power.limit --format=csv,noheader,nounits | xargs)

restore_power() {
    echo "Restoring GPU power limit to ${OLD_LIMIT} W"
    sudo nvidia-smi -i "$GPU" -pl "$LIMIT" >/dev/null
}

# EXIT trap remains active if the command fails or the script is interrupted.
echo "Setting GPU power limit to ${LIMIT} W"
sudo nvidia-smi -i "$GPU" -pl "$LIMIT" >/dev/null
trap restore_power EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

"${COMMAND[@]}"
