#!/usr/bin/env bash
# comfy-node-install: install custom ComfyUI nodes and fail with non-zero
# exit code if any of them cannot be installed. On failure it prints the
# list of nodes that could not be installed and hints the user to consult
# https://registry.comfy.org/ for correct names.
set -euo pipefail

if [[ $# -eq 0 ]]; then
  echo "Usage: comfy-node-install <node1> [<node2> …]" >&2
  exit 64  # EX_USAGE
fi

custom_nodes_dir="${COMFYUI_CUSTOM_NODES_DIR:-/comfyui/custom_nodes}"
runtime_python="${COMFYUI_RUNTIME_PYTHON:-/opt/venv/bin/python}"

log=$(mktemp)

# Let comfy-cli use the ComfyUI workspace environment to install the node.
# The worker runtime uses /opt/venv, so mirror node requirements there below.
set +e
env -u VIRTUAL_ENV comfy node install --mode=remote "$@" 2>&1 | tee "$log"
cli_status=$?
set -e

# extract node names that failed to install (one per line, uniq-sorted)
failed_nodes=$(grep -oP "(?<=An error occurred while installing ')[^']+" "$log" | sort -u || true)

# Fallback: capture names from "Node '<name>@' not found" lines if previous grep found nothing
if [[ -z "$failed_nodes" ]]; then
  failed_nodes=$(grep -oP "(?<=Node ')[^@']+" "$log" | sort -u || true)
fi

if [[ -n "$failed_nodes" ]]; then
  echo "Comfy node installation failed for the following nodes:" >&2
  echo "$failed_nodes" | while read -r n; do echo "  • $n" >&2 ; done
  echo >&2
  echo "Please verify the node names at https://registry.comfy.org/ and try again." >&2
  exit 1
fi

for requirements_file in "$custom_nodes_dir"/*/requirements.txt; do
  if [[ ! -f "$requirements_file" ]]; then
    continue
  fi
  uv pip install --python "$runtime_python" -r "$requirements_file"
done

# If we reach here no failed nodes were detected. Warn if CLI exit status
# was non-zero but treat it as success.
if [[ $cli_status -ne 0 ]]; then
  echo "Warning: comfy node install exited with status $cli_status but no errors were detected in the log — assuming success." >&2
fi

exit 0
