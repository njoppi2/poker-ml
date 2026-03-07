#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_TAG="${1:-research-artifacts}"
BASE_URL="https://github.com/njoppi2/poker-ml/releases/download/${RELEASE_TAG}"

download_and_extract() {
  local archive_name="$1"
  local target_path="$2"
  local archive_path

  archive_path="$(mktemp)"
  trap 'rm -f "${archive_path}"' RETURN

  curl -fsSL "${BASE_URL}/${archive_name}" -o "${archive_path}"
  mkdir -p "${REPO_ROOT}/${target_path}"
  tar -xzf "${archive_path}" -C "${REPO_ROOT}/${target_path}"
}

download_and_extract "analysis-logs.tar.gz" "game_engine/ia/analysis/logs"
download_and_extract "analysis-blueprints-extra.tar.gz" "game_engine/ia/analysis/blueprints/important_blueprints"
