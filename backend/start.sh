#!/bin/bash
set -e

echo "Starting DCLG Outfit Recommender..."
echo "Using pre-built compatibility graph (799 products, 525K edges)"

# Start the server
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
