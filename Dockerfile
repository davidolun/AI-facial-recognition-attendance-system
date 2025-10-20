FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System dependencies for numpy/opencv/dlib/pillow/lxml/psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    curl \
    pkg-config \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libtiff-dev \
    libopenblas-dev \
    liblapack-dev \
    libatlas-base-dev \
    libboost-all-dev \
    libx11-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libpq-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --prefer-binary -r requirements.txt

# Copy project
COPY . .

# Collect static (non-fatal in case settings block it)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8000

CMD ["gunicorn", "attendance_system.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
