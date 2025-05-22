#!/usr/bin/env bash
# comfy-manager-set-mode: Set ComfyUI-Manager network_mode in its config.ini.
# Usage: comfy-manager-set-mode <public|private|offline>
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: comfy-manager-set-mode <public|private|offline>" >&2
  exit 64
fi
MODE="$1"
if [[ "$MODE" != "public" && "$MODE" != "private" && "$MODE" != "offline" ]]; then
  echo "Invalid mode: $MODE. Must be public, private, or offline." >&2
  exit 64
fi

CFG_FILE="${COMFYUI_MANAGER_CONFIG:-/comfyui/user/default/ComfyUI-Manager/config.ini}"
mkdir -p "$(dirname "$CFG_FILE")"
if [[ -f "$CFG_FILE" ]]; then
  if grep -q "^network_mode" "$CFG_FILE"; then
    sed -i "s/^network_mode *=.*/network_mode = $MODE/" "$CFG_FILE"
  else
    # Ensure [default] section exists
    if ! grep -q "^\[default\]" "$CFG_FILE"; then
      printf "[default]\n" >> "$CFG_FILE"
    fi
    printf "network_mode = %s\n" "$MODE" >> "$CFG_FILE"
  fi
else
  printf "[default]\nnetwork_mode = %s\n" "$MODE" > "$CFG_FILE"
fi

echo "worker-comfyui - ComfyUI-Manager network_mode set to '$MODE' in $CFG_FILE" 