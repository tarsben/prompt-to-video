#!/usr/bin/env bash
# Re-vendor Remotion agent skills from GitHub, pinned to the latest main SHA.
# Run monthly (or on demand), then `modal deploy modal_app.py` to ship.
set -euo pipefail
cd "$(dirname "$0")"
SHA=$(curl -s "https://api.github.com/repos/remotion-dev/remotion/commits/main" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['sha'])")
for s in remotion-best-practices remotion-markup remotion-captions remotion-render; do
  curl -s -o "remotion/$s.md" \
    "https://raw.githubusercontent.com/remotion-dev/remotion/$SHA/packages/skills/skills/$s/SKILL.md"
done
echo "$SHA" > remotion/SHA
date -u +%Y-%m-%dT%H:%M:%SZ > remotion/FETCHED_AT
echo "Pinned to $SHA"
