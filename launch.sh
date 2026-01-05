#!/bin/bash
set -e

# Configuration
VENV_NAME="venv_media_organizer"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# 1. Check for Python
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# 2. Create Virtual Environment if it doesn't exist
if [ ! -d "$SCRIPT_DIR/$VENV_NAME" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/$VENV_NAME"
    
    # Activate and install requirements
    source "$SCRIPT_DIR/$VENV_NAME/bin/activate"
    
    echo "Installing dependencies..."
    if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
        pip install -r "$SCRIPT_DIR/requirements.txt"
    else
        echo "requirements.txt not found! Installing Pillow manually."
        pip install Pillow
    fi
else
    # Just activate
    source "$SCRIPT_DIR/$VENV_NAME/bin/activate"
fi

# 3. Launch Application
echo "Starting Media Organizer..."
python "$SCRIPT_DIR/media_organizer.py"
