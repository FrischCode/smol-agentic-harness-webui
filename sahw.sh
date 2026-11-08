#!/bin/sh
# SAHW launcher: finds the SAH tree (smol-agentic-harness) and starts the server on it.
# Point SAH_INSTALL_DIR at the tree if it is not on PATH; extra arguments pass straight through:
#   sahw.sh --port 8391
SAH_INSTALL_DIR="C:/Work/SAH"
if [ ! -d "$SAH_INSTALL_DIR" ]; then
  sah_cmd=$(command -v sah) || sah_cmd=""
  [ -n "$sah_cmd" ] && SAH_INSTALL_DIR=$(dirname "$sah_cmd")
fi
if [ ! -d "$SAH_INSTALL_DIR" ]; then
  echo "hey user - this needs https://github.com/FrischCode/smol-agentic-harness installed:"
  echo "point SAH_INSTALL_DIR above to its location by editing this file, or add it to PATH - otherwise this won't start."
  exit 1
fi
cd "$(dirname "$0")" || exit 1
exec .venv/Scripts/python.exe -m sahw --runs-root "$SAH_INSTALL_DIR/runs" --sah-tree "$SAH_INSTALL_DIR" "$@"
