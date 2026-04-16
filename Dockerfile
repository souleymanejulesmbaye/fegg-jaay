FROM python:3.12-slim

# Dépendances système
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code
COPY . .

# Port exposé par Railway
EXPOSE 8000

# Au démarrage : migrate + collectstatic + gunicorn (les env vars sont dispo ici)
CMD python manage.py migrate --noinput && \
    python manage.py collectstatic --noinput && \
    gunicorn fegg_jaay.wsgi:application --bind 0.0.0.0:$PORT --workers 2
