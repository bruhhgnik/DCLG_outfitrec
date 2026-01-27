FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Run startup script (generates graph JSON then starts server)
CMD ["./start.sh"]
