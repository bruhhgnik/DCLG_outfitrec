#!/bin/bash
set -e

echo "Starting DCLG Outfit Recommender..."

# Generate compatibility graph JSON if it doesn't exist
if [ ! -f "compatibility_graph.json" ]; then
    echo "Generating compatibility graph from database..."
    python export_graph_to_json.py
    echo "Graph generated successfully!"
else
    echo "Using existing compatibility graph."
fi

# Start the server
echo "Starting uvicorn server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8080
