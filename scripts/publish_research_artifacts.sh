#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RELEASE_TAG="${1:-research-artifacts}"
SOURCE_REF="${2:-HEAD}"
WORK_DIR="$(mktemp -d)"

cleanup() {
  rm -rf "${WORK_DIR}"
}

trap cleanup EXIT

archive_from_ref() {
  local source_path="$1"
  local archive_name="$2"
  local extract_dir="${WORK_DIR}/extract"
  local source_dir

  rm -rf "${extract_dir}"
  mkdir -p "${extract_dir}"

  if ! git -C "${REPO_ROOT}" ls-tree -r --name-only "${SOURCE_REF}" "${source_path}" | grep -q .; then
    echo "Could not find ${source_path} in ${SOURCE_REF}" >&2
    echo "Pass the pre-cleanup commit as the second argument." >&2
    exit 1
  fi

  git -C "${REPO_ROOT}" archive "${SOURCE_REF}" "${source_path}" | tar -xf - -C "${extract_dir}"
  source_dir="${extract_dir}/${source_path}"
  tar -czf "${WORK_DIR}/${archive_name}" -C "${source_dir}" .
}

archive_from_ref "game_engine/ia/analysis/logs" "analysis-logs.tar.gz"
archive_from_ref \
  "game_engine/ia/analysis/blueprints/important_blueprints" \
  "analysis-blueprints-extra.tar.gz"

if gh release view "${RELEASE_TAG}" --repo njoppi2/poker-ml >/dev/null 2>&1; then
  gh release upload \
    "${RELEASE_TAG}" \
    "${WORK_DIR}/analysis-logs.tar.gz" \
    "${WORK_DIR}/analysis-blueprints-extra.tar.gz" \
    --clobber \
    --repo njoppi2/poker-ml
else
  gh release create \
    "${RELEASE_TAG}" \
    "${WORK_DIR}/analysis-logs.tar.gz" \
    "${WORK_DIR}/analysis-blueprints-extra.tar.gz" \
    --title "Research Artifacts" \
    --notes "Archived research logs and extra blueprint snapshots removed from the active source tree." \
    --repo njoppi2/poker-ml
fi
