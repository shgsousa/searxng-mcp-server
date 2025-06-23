FROM python:3.12.11-slim-bookworm

WORKDIR /app

# Install uv for faster package installation
RUN pip install --no-cache-dir uv

# Copy requirements first for better caching
COPY requirements.txt .
RUN uv pip install --no-cache --system -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose the port used by the application
EXPOSE 7870

# Set environment variables with defaults
ENV SEARXNG_URL=http://searxng:8080

# Command to run the application
CMD ["python", "main.py"]
