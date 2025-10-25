# TruthGraph v0 htmx Frontend Dockerfile
# Flask + htmx for server-side rendered UI

FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy requirements
COPY frontend/requirements.txt ./requirements.txt

# Install Python dependencies
RUN /root/.local/bin/uv pip install --system --no-cache -r requirements.txt

# Copy application code
COPY frontend/app.py ./app.py
COPY frontend/templates ./templates
COPY frontend/static ./static

# Expose port
EXPOSE 5000

# Run Flask application
CMD ["python", "app.py"]
