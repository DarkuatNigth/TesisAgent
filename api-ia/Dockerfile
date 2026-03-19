# Usa una imagen oficial y ligera de Python 3.10
FROM python:3.10-slim

# Evita que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1
# Asegura que la salida de la consola no se quede en el buffer (útil para ver logs en Docker)
ENV PYTHONUNBUFFERED=1

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala las dependencias del sistema necesarias para compilar paquetes y usar PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia los requerimientos e instálalos
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo el código fuente de tu proyecto al contenedor
COPY . /app/

# Expone el puerto 8000
EXPOSE 8000