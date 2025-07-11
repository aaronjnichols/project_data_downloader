FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgdal-dev \
    gdal-bin \
    libproj-dev \
    proj-data \
    proj-bin \
    libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG /usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH /usr/include/gdal
ENV C_INCLUDE_PATH /usr/include/gdal

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p output/jobs output/results logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"] 