#!/bin/bash

echo "🧹 Cleaning up previous build..."
# Force remove build and dist directories
rm -rf ./build/
rm -rf ./dist/
# Clean any Python cache files too
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
python clean.py

echo "🗑️ Removing Poetry environment..."
poetry env remove python

echo "🔄 Creating fresh Poetry environment..."
# Explicitly use Python 3.11
poetry env use /opt/homebrew/opt/python@3.11/bin/python3.11
poetry install

echo "🏗️ Building app..."
poetry run python setup.py py2app -A

# Add error checking before trying to run
if [ ! -f "./dist/GitHub PR Watcher.app/Contents/MacOS/GitHub PR Watcher" ]; then
    echo "❌ Build failed - executable not found"
    exit 1
fi

echo "🚀 Running app directly..."
poetry run python github_watcher/main.py