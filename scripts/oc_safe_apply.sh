#!/usr/bin/env bash
# Verify a signed configuration, then atomically replace one target file.
# Dry-run is the default. This script never downloads or executes updates.
set -euo pipefail

MODE="--check"
SOURCE=""
SIGNATURE=""
PUBLIC_KEY=""
TARGET=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check|--apply) MODE="$1"; shift ;;
    --source) SOURCE="$2"; shift 2 ;;
    --signature) SIGNATURE="$2"; shift 2 ;;
    --public-key) PUBLIC_KEY="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

for file in "$SOURCE" "$SIGNATURE" "$PUBLIC_KEY"; do
  [[ -n "$file" && -f "$file" ]] || { echo "Missing input file: $file" >&2; exit 2; }
done
[[ -n "$TARGET" ]] || { echo "Missing --target" >&2; exit 2; }
command -v openssl >/dev/null 2>&1 || { echo "OpenSSL is required" >&2; exit 1; }

openssl pkeyutl -verify -pubin -inkey "$PUBLIC_KEY" -rawin -in "$SOURCE" -sigfile "$SIGNATURE" >/dev/null
sha256sum "$SOURCE"

if [[ "$MODE" == "--check" ]]; then
  echo "Dry-run only. No file was changed. Use --apply explicitly to install."
  exit 0
fi

[[ "$EUID" -eq 0 ]] || { echo "--apply requires root" >&2; exit 1; }
TARGET_DIR="$(dirname "$TARGET")"
mkdir -p "$TARGET_DIR"
TEMP_FILE="$(mktemp "$TARGET_DIR/.openconnect-config.XXXXXX")"
BACKUP=""
COMMITTED=0

cleanup() {
  if [[ "$COMMITTED" -ne 1 && -n "$BACKUP" && -f "$BACKUP" ]]; then cp -a "$BACKUP" "$TARGET" || true; fi
  [[ -z "$TEMP_FILE" || ! -e "$TEMP_FILE" ]] || rm -f "$TEMP_FILE"
}
trap cleanup EXIT

install -m 0640 "$SOURCE" "$TEMP_FILE"
if [[ -e "$TARGET" ]]; then
  BACKUP="$TARGET.bak.$(date -u +%Y%m%dT%H%M%SZ)"
  cp -a "$TARGET" "$BACKUP"
fi
mv -f "$TEMP_FILE" "$TARGET"
TEMP_FILE=""
sync
COMMITTED=1
echo "Applied atomically to: $TARGET"
if [[ -n "$BACKUP" ]]; then echo "Previous version preserved at: $BACKUP"; fi
echo "No network interfaces or services were modified or restarted."
