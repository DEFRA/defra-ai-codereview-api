#!/bin/bash

# Stop any running MongoDB container
echo "Stopping MongoDB container..."
docker stop $(docker ps -q --filter name=mongodb) 2>/dev/null || true

# Remove MongoDB container
echo "Removing MongoDB container..."
docker rm $(docker ps -a -q --filter name=mongodb) 2>/dev/null || true

# Remove MongoDB image
echo "Removing MongoDB image..."
docker rmi $(docker images -q mongo) 2>/dev/null || true

# Remove MongoDB volume
echo "Removing MongoDB volume..."
docker volume rm $(docker volume ls -q --filter name=mongodb) 2>/dev/null || true

echo "MongoDB cleanup complete!"
