FROM python:3.10-slim

# Instalează dependențele de sistem necesare pentru Playwright
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libx11-xcb1 libxcomposite1 libxrandr2 libgbm-dev libpangocairo-1.0-0 libgtk-3-0 \
    libasound2 fonts-liberation libappindicator3-1 libxshmfence-dev libxdamage-dev libxext6 libegl1 \
    && apt-get clean

# Instalează dependențele Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalează Playwright și browserele
RUN pip install playwright
RUN playwright install --with-deps

# Configurații Playwright (setate ca variabile de mediu)
ENV SCREEN_WIDTH=1920
ENV SCREEN_HEIGHT=1024
ENV SCREEN_DEPTH=16
ENV MAX_CONCURRENT_CHROME_PROCESSES=10
ENV ENABLE_DEBUGGER=false
ENV PREBOOT_CHROME=true
ENV CONNECTION_TIMEOUT=300000
ENV MAX_CONCURRENT_SESSIONS=10
ENV CHROME_REFRESH_TIME=600000
ENV DEFAULT_BLOCK_ADS=true
ENV DEFAULT_STEALTH=true
ENV DEFAULT_IGNORE_HTTPS_ERRORS=true

# Copiază codul aplicației
COPY . /app
WORKDIR /app

# Rulează aplicația
CMD ["python", "-u", "script.py"]
