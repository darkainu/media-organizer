#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
source ~/miniconda3/etc/profile.d/conda.sh
conda activate media-organizer
python "$SCRIPT_DIR/media_organizer.py"
