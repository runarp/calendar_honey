#!/bin/bash
# Test runner script for calendar_honey
# Ensures tests run in a virtual environment

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if venv exists, create if not
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q || {
    echo "Warning: Some dependencies may have conflicts. Installing core packages individually..."
    pip install pyyaml chromadb pydantic-settings sentence-transformers pytest pytest-asyncio -q
}

# Run tests
echo "Running tests..."
pytest "$@"

