# Base image
FROM python:3.12-slim

# Install libraries in requirements.txt
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app directory to container
COPY app/ app/
COPY templates/ templates/

# Run fastapi server with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

