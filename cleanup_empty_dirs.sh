#!/bin/bash
# Cleanup script for empty directories
# Run this to remove unnecessary empty directories from the project

set -e  # Exit on error

echo "========================================"
echo "Empty Directories Cleanup Script"
echo "========================================"
echo ""

# Directories to definitely remove (structural errors + unnecessary)
REMOVE_DIRS=(
    "domain/workflows/image/processors"
    "domain/workflows/video/processors"
    "infrastructure/storage"
    "infrastructure/telegram"
    "config"
    "domain/payments"
    "webhooks"
)

echo "Removing unnecessary directories..."
echo ""

REMOVED=0
SKIPPED=0

for dir in "${REMOVE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        if [ -z "$(ls -A $dir)" ]; then
            echo "✓ Removing: $dir"
            rmdir "$dir"
            REMOVED=$((REMOVED + 1))
        else
            echo "⚠ Skipping: $dir (not empty)"
            SKIPPED=$((SKIPPED + 1))
        fi
    else
        echo "- Already gone: $dir"
    fi
done

echo ""
echo "========================================"
echo "Summary:"
echo "  Removed: $REMOVED directories"
echo "  Skipped: $SKIPPED directories (not empty)"
echo "========================================"
echo ""

# Optional: Remove API directories
echo "Optional: Remove API directories?"
echo "  (Only if you don't plan to add REST API in future)"
echo ""
read -p "Remove api/ directories? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    API_DIRS=(
        "api/handlers"
        "api/middleware"
        "api/responses"
    )

    echo ""
    echo "Removing API directories..."
    for dir in "${API_DIRS[@]}"; do
        if [ -d "$dir" ] && [ -z "$(ls -A $dir)" ]; then
            echo "✓ Removing: $dir"
            rmdir "$dir"
        fi
    done

    # Try to remove api/ parent if empty
    if [ -d "api" ] && [ -z "$(ls -A api)" ]; then
        echo "✓ Removing: api/"
        rmdir "api"
    fi
fi

echo ""
echo "========================================"
echo "Kept directories (for future use):"
echo "========================================"
echo "  ✓ tests/integration/     - For integration tests"
echo "  ✓ tests/unit/database/   - For database unit tests"
echo "  ✓ scripts/               - For utility scripts"
if [ -d "api" ]; then
    echo "  ✓ api/                   - For REST API (if planned)"
fi
echo ""
echo "✅ Cleanup complete!"
echo ""
echo "Next steps:"
echo "  1. Review changes: git status"
echo "  2. Commit if satisfied: git add -A && git commit -m 'Clean up empty directories'"
echo ""
