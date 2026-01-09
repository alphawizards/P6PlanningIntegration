FROM python:3.11-slim

WORKDIR /app

# Install system dependencies if required (e.g., for SQLite)
# RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Set default environment variables
ENV PYTHONUNBUFFERED=1
ENV P6_CONNECTION_MODE=SQLITE

# Default command: Run in AI Chat Mode
CMD ["python", "main.py", "--chat"]
