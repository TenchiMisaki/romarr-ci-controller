#!/usr/bin/env bash
set -euo pipefail
python - <<'PY'
from romarr.library import bsdtar_path, rar_tool

bsdtar = bsdtar_path()
rar = rar_tool()
if bsdtar is None:
    raise SystemExit('FAIL: ROMarr did not recognize libarchive bsdtar')
if rar is None:
    raise SystemExit('FAIL: ROMarr did not recognize a split-RAR reader')
print('ROMarr archive tool detection PASS; split-RAR reader:', rar.kind)
PY
