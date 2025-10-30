# Base image
FROM python:3.12-slim

# Install libraries in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app directory to container
COPY app/ app/
COPY templates/ templates/

# Create log directory and set permissions
RUN mkdir -p /app/logs && \
    groupadd -r app && useradd -r -g app app && \
    chown -R app:app /app/logs /app

# create app user and run container with app user
USER app
CMD ["sh", "-c", "chown -R app:app /app/logs && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

