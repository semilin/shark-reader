#!/bin/bash

# Script to generate web/static/texts/index.json from the texts directory
# This extracts metadata from each .annotated.json file and creates an index

TEXTS_DIR="web/static/texts"
OUTPUT_FILE="$TEXTS_DIR/index.json"

# Create a temporary file for collecting entries
temp_file=$(mktemp)

# Process each annotated.json file
for file in "$TEXTS_DIR"/*.annotated.json; do
    # Skip if no files found
    [ -e "$file" ] || continue
    
    # Extract filename without extension for the path
    filename=$(basename "$file" .annotated.json)
    
    # Extract metadata using Python and append to temp file
    python3 -c "
import json

try:
    with open('$file', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    metadata = data.get('metadata', {})
    
    # Build the entry with path (relative to static directory)
    entry = {
        'title': metadata.get('title', 'Unknown'),
        'author': metadata.get('author', 'Unknown'),
        'language': metadata.get('language', 'unknown'),
        'work_type': metadata.get('work_type', 'prose'),
        'path': f'/shark-reader/texts/${filename}.annotated.json'
    }
    
    # Output as JSON
    print(json.dumps(entry, ensure_ascii=False))
except Exception as e:
    print(f'Error processing $file: {e}', file=sys.stderr)
" >> "$temp_file"
done

# Build the final JSON file using Python for proper formatting
python3 << PYTHON_SCRIPT
import json

# Read all entries from temp file
entries = []
with open('$temp_file', 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                entry = json.loads(line)
                entries.append(entry)
            except json.JSONDecodeError:
                pass

# Write properly formatted JSON array
with open('$OUTPUT_FILE', 'w', encoding='utf-8') as f:
    json.dump(entries, f, ensure_ascii=False, indent=2)

print(f'Generated $OUTPUT_FILE with {len(entries)} texts')
PYTHON_SCRIPT

# Clean up temp file
rm "$temp_file"
