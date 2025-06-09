# ─── Dockerfile ───────────────────────────────────────────────────────────────
FROM python:3.10-slim

WORKDIR /app

# Installs curl library
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# 1) Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Copy all of our Python code into /app
COPY . .

# 3) Expose the ports
EXPOSE 5002 5003 5004

# 4) Default entrypoint = python.
ENTRYPOINT ["python"]
# ────────────────────────────────────────────────────────────────────────────────