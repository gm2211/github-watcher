#!/bin/bash
set -e

# Store formula file path
FORMULA_FILE="Formula/github-pr-watcher.rb"

# Function to restore formula and cleanup
cleanup() {
    local exit_code=$?
    echo "🧹 Cleaning up..."
    
    # Restore original formula if we have it
    if [ -n "$ORIGINAL_FORMULA" ] && [ -f "$FORMULA_FILE" ]; then
        echo "📝 Restoring original formula..."
        echo "$ORIGINAL_FORMULA" > "$FORMULA_FILE"
    fi
    
    # Remove temp directory if it exists
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
    
    exit $exit_code
}

# Set trap to ensure cleanup happens on exit
trap cleanup EXIT

# Check if formula exists
if [ ! -f "$FORMULA_FILE" ]; then
    echo "❌ Formula file not found: $FORMULA_FILE"
    exit 1
fi

echo "🧹 Cleaning up previous installation..."
brew uninstall github-pr-watcher --force 2>/dev/null || true

echo "🔧 Preparing local archive..."
# Store original formula content
ORIGINAL_FORMULA=$(cat "$FORMULA_FILE")

# Create a temporary directory for the archive
TEMP_DIR=$(mktemp -d)
ARCHIVE_PATH="$TEMP_DIR/github-pr-watcher.tar.gz"

# Create archive using git archive
git archive --format=tar.gz --prefix=github-pr-watcher-1.0.0/ -o "$ARCHIVE_PATH" HEAD

# Calculate SHA256
SHA256=$(shasum -a 256 "$ARCHIVE_PATH" | cut -d' ' -f1)

echo "📝 Updating formula for local testing..."
# Update formula with local archive path and SHA
sed -i '' \
    -e "s|url \".*\"|url \"file://$ARCHIVE_PATH\"|" \
    -e "s|sha256 \".*\"|sha256 \"$SHA256\"|" \
    "$FORMULA_FILE"

echo "🔨 Installing formula..."
HOMEBREW_NO_AUTO_UPDATE=1 HOMEBREW_NO_INSTALL_FROM_API=1 brew install --verbose "$FORMULA_FILE"

echo "🚀 Running app..."
github-pr-watcher