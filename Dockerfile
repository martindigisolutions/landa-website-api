# ============================================
# Landa Beauty Supply API - Dockerfile
# Optimized for AWS App Runner
# ============================================

# Use Python 3.11 slim image for smaller size
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8080

# Set working directory
WORKDIR /app

# Install system dependencies (if needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first (for better Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Remove unnecessary files for production
RUN rm -rf \
    .env* \
    .git \
    .gitignore \
    __pycache__ \
    *.sqlite3 \
    tests \
    .pytest_cache \
    .venv \
    *.md \
    docs

# Create non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (App Runner uses 8080 by default)
EXPOSE 8080

# Health check for App Runner
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/health')" || exit 1

# Run the application
CMD ["python", "main.py"]

