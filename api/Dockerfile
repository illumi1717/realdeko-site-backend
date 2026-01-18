FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install Python dependencies.
COPY realdeko-site-backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy realdeko-site-backend sources so both the API and db driver are available.
COPY realdeko-site-backend /app/realdeko-site-backend

WORKDIR /app/realdeko-site-backend/api

# Defaults let the container talk to a MongoDB running on the host.
# Override MONGODB_URI/MONGODB_DB/MONGODB_COLLECTION at runtime as needed.
ENV PYTHONPATH=/app/realdeko-site-backend \
    MONGODB_URI=mongodb://host.docker.internal:27017/ \
    MONGODB_DB=realdeko \
    MONGODB_COLLECTION=posts

EXPOSE 80

# Expect a FastAPI app named `app` in main.py. Override CMD if different.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

