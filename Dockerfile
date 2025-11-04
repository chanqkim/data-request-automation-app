# Base image
FROM python:3.12-slim

# Install libraries in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app directory to container
COPY app/ app/
COPY templates/ templates/

# Create log and file-export directory and set permissions
RUN groupadd -r app \
    && useradd --no-log-init -r -g app app \
    && mkdir -p /app/logs /app/export_file_path \
    && chown -R app:app /app

# create app user and run container with app user
USER app
CMD ["sh", "-c", "chown -R app:app /app/logs /app/export_file_path && uvicorn app.main:app --host 0.0.0.0 --port 8000"]

