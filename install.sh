#!/bin/bash

set -e

# Install Miniconda if not present
if ! command -v conda &> /dev/null; then
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -b
    rm Miniconda3-latest-Linux-x86_64.sh
fi

# Remove existing environment if it exists
conda env remove -n media-organizer --yes

# Create fresh conda environment
conda env create -f environment.yml

# Activate environment
source $(conda info --base)/etc/profile.d/conda.sh
conda activate media-organizer

echo "Installation complete! Run ./launch.sh to start the application"
