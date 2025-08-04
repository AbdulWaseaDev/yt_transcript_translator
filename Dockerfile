# Use secure, minimal Python Alpine image
FROM python:3.12-alpine

# Set working directory
WORKDIR /app

# Install minimal build dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    libffi-dev \
    make \
    bash \
    curl \
    && pip install --upgrade pip

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Expose the Gunicorn port
EXPOSE 5001

# Run with Gunicorn in production mode
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "app:app", "--workers", "3"]