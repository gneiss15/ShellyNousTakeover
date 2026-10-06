#!/usr/bin/env bash
# Environment.sh, Version: 1.00
# Load explicit external locations without reading private file contents.
if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  echo 'Source this file from a project tool.' >&2
  exit 2
fi
TakeoverRoot="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
: "${TAKEOVER_PRIVATE_DIR:?Set TAKEOVER_PRIVATE_DIR to your external private directory}"
: "${TAKEOVER_IDF_PATH:?Set TAKEOVER_IDF_PATH to ESP-IDF 5.5.1}"
: "${TAKEOVER_IDF_TOOLS_PATH:?Set TAKEOVER_IDF_TOOLS_PATH to the ESP-IDF tools directory}"
[[ -d "$TAKEOVER_PRIVATE_DIR" ]] || { echo 'Private directory not found.' >&2; return 1; }
TakeoverPrivate="$(cd -- "$TAKEOVER_PRIVATE_DIR" && pwd -P)"
case "$TakeoverPrivate/" in
  "$TakeoverRoot/"*) echo 'Private directory must be outside the project.' >&2; return 1 ;;
esac
for TakeoverFile in Secrets.local.json private.key public.key; do
  [[ -f "$TakeoverPrivate/$TakeoverFile" && -r "$TakeoverPrivate/$TakeoverFile" ]] || {
    echo "Required private file missing/unreadable: $TakeoverFile" >&2; return 1;
  }
done
[[ -f "$TAKEOVER_IDF_PATH/export.sh" ]] || { echo 'ESP-IDF export.sh not found.' >&2; return 1; }
[[ -d "$TAKEOVER_IDF_TOOLS_PATH" ]] || { echo 'ESP-IDF tools directory not found.' >&2; return 1; }
export IDF_TOOLS_PATH="$TAKEOVER_IDF_TOOLS_PATH"
