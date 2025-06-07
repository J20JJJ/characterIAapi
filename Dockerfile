# Dockerfile

# 1. Imagen base ligera
FROM python:3.11-slim

# 2. Para ver logs sin buffer
ENV PYTHONUNBUFFERED=1

# 3. Instala dependencias de sistema (si acaso)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# 4. Crea y define directorio de trabajo
WORKDIR /app

# 5. Copia e instala requisitos Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copia el resto de tu código
COPY . .

# 7. Expone el puerto 8000
EXPOSE 8000

# 8. Arranca con Gunicorn usando el worker de Uvicorn para soportar async
#    Asume que tu Flask app está en app.py con "app = Flask(__name__)"
CMD ["gunicorn", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "app:app"]
