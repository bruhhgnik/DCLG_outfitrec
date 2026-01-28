FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy seed data
COPY compatibility_graph_scored.json .
COPY products_seed.json .

# Copy seed script
COPY seed_db.py .

WORKDIR /app/backend

# Seed database and start server
CMD ["sh", "-c", "cd /app && python seed_db.py && cd /app/backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
