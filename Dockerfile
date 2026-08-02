# Use official Python image
FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy project files
COPY . /app

# Expose the port (Render provides $PORT; default to 8080)
EXPOSE 8080

# Start gunicorn using the module path app.index:app and bind to $PORT if set
CMD ["sh", "-c", "gunicorn -w 2 -b 0.0.0.0:${PORT:-8080} app.index:app"]
