#!/bin/bash
set -e

echo "🧹 Cleaning up..."
rm -rf build dist *.egg-info poetry.lock

echo "🔄 Setting up Python environment..."
poetry env use python3.11

echo "📦 Installing dependencies..."
poetry lock --no-update
poetry install

echo "🔨 Building executable..."
poetry run pyinstaller github-pr-watcher.spec

echo "🚀 Running executable..."
./dist/github-pr-watcher