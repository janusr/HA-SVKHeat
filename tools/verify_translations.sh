#!/usr/bin/env bash
set -euo pipefail

echo "== Checking for manual name overrides =="
if grep -Rin "_attr_name\s*=" custom_components/svk_heatpump/ >/dev/null; then
  echo "Found _attr_name assignments. Please remove them."
  grep -Rin "_attr_name\s*=" custom_components/svk_heatpump/
  exit 1
else
  echo "OK: No _attr_name overrides found."
fi

echo "== Checking EntityDescriptions for translation_key and name=None =="
MISSING=0
for f in custom_components/svk_heatpump/{sensor,binary_sensor,number,select,switch}.py; do
  if [ -f "$f" ]; then
    # Find all EntityDescription instances and check each one
    ENTITY_DESC_LINES=$(grep -n "EntityDescription(" "$f")
    while IFS= read -r line; do
      LINE_NUM=$(echo "$line" | cut -d: -f1)
      
      # Check if this EntityDescription has the correct translation_key
      # Look for translation_key=self._entity_key in the next few lines (within the EntityDescription)
      DESC_BLOCK=$(sed -n "${LINE_NUM},$((LINE_NUM + 10))p" "$f")
      if ! echo "$DESC_BLOCK" | grep -q "translation_key=self\._entity_key"; then
        # Check if it's a system entity that should have a hardcoded translation_key
        if ! echo "$DESC_BLOCK" | grep -q "translation_key=\""; then
          echo "Missing translation_key in EntityDescription at $f:$LINE_NUM"
          MISSING=1
        fi
      fi
      
      # Check if this EntityDescription has hardcoded name (excluding name=None)
      if echo "$DESC_BLOCK" | grep -E "name\s*=\s*['\\\"]" | grep -v "name\s*=\s*None" >/dev/null; then
        echo "Hardcoded name= in EntityDescription at $f:$LINE_NUM"
        echo "$DESC_BLOCK" | grep -E "name\s*=\s*['\\\"]" | grep -v "name\s*=\s*None"
        MISSING=1
      fi
    done <<< "$ENTITY_DESC_LINES"
  fi
done


if [ $MISSING -eq 0 ]; then
  echo "OK: All EntityDescriptions look good."
else
  echo "ERROR: Fix the issues above."
  exit 1
fi

echo "== Running hassfest =="
# Skip hassfest if not available (e.g., in development environment)
if python3 -c "import script.hassfest" 2>/dev/null; then
  python3 -m script.hassfest || { echo "hassfest failed"; exit 1; }
  echo "hassfest passed."
else
  echo "hassfest not available, skipping."
fi

echo "All checks passed."