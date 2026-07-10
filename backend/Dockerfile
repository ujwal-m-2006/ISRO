FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user (Debian tools — this image is python:3.11-slim, not Alpine)
RUN groupadd -g 1001 appgroup && useradd -u 1001 -g appgroup -m appuser

# Change ownership and switch to non-root user
WORKDIR /home/appuser
COPY --chown=appuser:appgroup . .
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Run the application — shell form so $PORT expands (Render assigns this
# dynamically); --reload is dev-only overhead with no benefit in a container
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}