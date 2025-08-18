#!/bin/bash

# Build script for Kion MCP Server DXT package
# Creates temporary DXT structure, builds package, and cleans up

set -e  # Exit on any error

echo "🚀 Building Kion MCP Server DXT package..."

# Create temporary directory
TEMP_DIR=$(mktemp -d)
echo "Created temporary directory: $TEMP_DIR"

# Function to cleanup on exit
cleanup() {
    echo "Cleaning up temporary directory..."
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# Copy core files to temp directory
echo "Copying manifest and core files..."
cp manifest.json "$TEMP_DIR/"
cp pyproject.toml "$TEMP_DIR/"
cp README.md "$TEMP_DIR/"
cp uv.lock "$TEMP_DIR/"
cp .dxtignore "$TEMP_DIR/"
cp icon.png "$TEMP_DIR/"
cp LICENSE "$TEMP_DIR/"

# Create server directory structure
echo "Creating server directory structure..."
mkdir -p "$TEMP_DIR/server"

# Copy source code to src directory 
echo "Copying source code..."
mkdir -p "$TEMP_DIR/src"
cp -r src/kion_mcp "$TEMP_DIR/src/"

# Copy OpenAPI spec to expected location (3 levels up from server/kion_mcp/server.py)
echo "Copying OpenAPI specification..."
cp fixed_spec.json "$TEMP_DIR/"

# Change to temp directory and build DXT
echo "Building DXT package..."
cd "$TEMP_DIR"

# Run dxt pack
if command -v dxt &> /dev/null; then
    dxt pack
else
    echo "❌ DXT CLI not found. Please install with: npm install -g @anthropic-ai/dxt"
    exit 1
fi

# Move the generated .dxt file back to original directory with proper name
echo "Moving DXT package to project directory..."
DXT_FILE=$(find . -name "*.dxt" -type f | head -n 1)
if [ -n "$DXT_FILE" ]; then
    # Extract version from manifest.json
    VERSION=$(grep '"version"' manifest.json | head -1 | sed 's/.*"version": *"\([^"]*\)".*/\1/')
    NAME=$(grep '"name"' manifest.json | head -1 | sed 's/.*"name": *"\([^"]*\)".*/\1/')
    PROPER_NAME="${NAME}-${VERSION}.dxt"
    mv "$DXT_FILE" "$OLDPWD/$PROPER_NAME"
    echo "✅ Successfully created: $PROPER_NAME"
else
    echo "❌ No .dxt file found after packaging"
    exit 1
fi

echo "DXT package build complete!"