# Dockerfile
FROM python:3.13-slim

WORKDIR /app

# копираме requirements ако има
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# копираме кода
COPY . .

EXPOSE 8000

# командата за стартиране (можеш да смениш с gunicorn uvicorn workers за production)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
