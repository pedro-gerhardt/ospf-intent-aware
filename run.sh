#!/bin/bash

IMAGE_NAME="ospf-intent-aware-img"

echo ">>> Building Docker image: $IMAGE_NAME..."

docker build -t $IMAGE_NAME .

if [ $? -ne 0 ]; then
    echo "XXX Error building Docker image. Aborting."
    exit 1
fi

echo ">>> Docker image built successfully."
echo ">>> Running the container..."

docker run -it --rm --privileged $IMAGE_NAME