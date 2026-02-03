# Use Python 3.13 slim image
FROM python:3.13-slim-bookworm

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install -r requirements.txt

# Install Playwright browsers and dependencies
# We only install chromium to keep the image size optimized, as used in the code
RUN playwright install --with-deps chromium

# Copy the rest of the application
COPY . .

# Create a directory for data persistence
RUN mkdir -p data

# Define the entrypoint
ENTRYPOINT ["python", "main.py"]

# Default command (can be overridden)
CMD ["--help"]
