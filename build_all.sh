#!/bin/bash
set -euo pipefail

# Determine the directory of this script so that relative paths are correct
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
DOCKER_SRC_DIR="$SCRIPT_DIR/src"

# Loop over each subdirectory inside the src folder
for folder in "$DOCKER_SRC_DIR"/*; do
    if [ -d "$folder" ]; then
        folder_name=$(basename "$folder")
        
        # Skip 'redis' folder
        if [ "$folder_name" == "redis" ]; then
            echo "Skipping '$folder_name': Redis does not require build"
            continue
        fi

        dockerfile="$folder/Dockerfile"
        if [ -f "$dockerfile" ]; then
            # If Dockerfile references uv.lock, ensure the file exists in the project folder
            if grep -q "uv\.lock" "$dockerfile"; then
                if [ ! -f "$folder/uv.lock" ]; then
                    echo "Skipping '$folder_name': Dockerfile references uv.lock but file not found in $folder"
                    continue
                fi
            fi

            # Determine build context:
            # If the Dockerfile contains "COPY src/<folder_name>", it expects to be run from the repository root.
            if grep -E -q "COPY[[:space:]]+src/${folder_name}\b" "$dockerfile"; then
                context="$SCRIPT_DIR"
                echo "Building Docker image for '$folder_name' using $dockerfile with repository root as context"
            else
                context="$folder"
                echo "Building Docker image for '$folder_name' using $dockerfile with project folder as context"
            fi

            docker build -t "$folder_name" -f "$dockerfile" "$context"
        else
            echo "Skipping '$folder_name': Dockerfile not found"
        fi
    fi
done

