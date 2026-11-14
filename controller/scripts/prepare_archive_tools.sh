#!/usr/bin/env bash
set -euo pipefail
START_EPOCH="$(date +%s)"
finish() {
  result="$?"
  END_EPOCH="$(date +%s)"
  printf '%s\n' '================ DIAGNOSTIC FINISH ================'
  printf 'Finish time: %s; elapsed seconds: %s; exit code: %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%:z')" "$((END_EPOCH-START_EPOCH))" "$result"
}
trap finish EXIT
printf '%s\n' '================ PREFLIGHT CHECK ================'
printf 'Script: GitHub runner ROMarr archive prerequisites v01\n'
printf 'Expected: TenchiMisaki/romarr-ci-controller, GitHub Actions, Ubuntu 24.04, Linux\n'
printf 'Detected: repository=%s, actions=%s, runner_os=%s, time=%s\n' \
  "${GITHUB_REPOSITORY:-unset}" "${GITHUB_ACTIONS:-unset}" "${RUNNER_OS:-unset}" "$(date '+%Y-%m-%dT%H:%M:%S%:z')"
if [[ "${GITHUB_REPOSITORY:-}" != 'TenchiMisaki/romarr-ci-controller' || "${GITHUB_ACTIONS:-}" != 'true' || "${RUNNER_OS:-}" != 'Linux' ]]; then
  printf '%s\n' 'FAIL: unexpected runner identity' >&2
  exit 1
fi
source /etc/os-release
if [[ "$ID" != ubuntu || "$VERSION_ID" != '24.04' ]]; then
  printf 'FAIL: unsupported OS: %s %s\n' "$ID" "$VERSION_ID" >&2
  exit 1
fi
packages=()
if ! command -v bsdtar >/dev/null 2>&1; then packages+=(libarchive-tools); fi
if ! command -v 7z >/dev/null 2>&1; then packages+=(7zip); fi
if ! command -v unar >/dev/null 2>&1 || ! command -v lsar >/dev/null 2>&1; then packages+=(unar); fi
if (( ${#packages[@]} > 0 )); then
  command -v sudo >/dev/null 2>&1 || { printf '%s\n' 'FAIL: sudo unavailable' >&2; exit 1; }
  printf 'Missing packages: %s\n' "${packages[*]}"
  sudo apt-get update -qq
  sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"
else
  printf '%s\n' 'All required archive commands already present; no package changes'
fi
for binary in bsdtar 7z unar lsar; do
  command -v "$binary" >/dev/null 2>&1 || { printf 'FAIL: %s remains unavailable\n' "$binary" >&2; exit 1; }
  printf 'TOOL PASS: %s found\n' "$binary"
done
