#!/bin/bash
src="/src/tctk-stable-old"
dst="/src/tctk"

find "$src" -type f \( -name "*.sh" -o -name "*.yaml" -o -name "*.toml" -o -name "*.py" -o -name "*.json" -o -name "*.md" \) ! -path "*/.git/*" | while read -r file; do
    rel="${file#$src/}"
    mkdir -p "$dst/$(dirname "$rel")"
    cp -v "$file" "$dst/$rel"
done
