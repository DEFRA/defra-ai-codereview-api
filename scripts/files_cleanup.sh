#!/bin/bash

# Script to clean up data and logs directories
echo "Cleaning up data and logs directories..."

# Remove data directory if it exists
if [ -d "./data" ]; then
    echo "Removing data directory..."
    rm -rf ./data
fi

# Remove logs directory if it exists
if [ -d "./logs" ]; then
    echo "Removing logs directory..."
    rm -rf ./logs
fi

echo "Cleanup complete!" 