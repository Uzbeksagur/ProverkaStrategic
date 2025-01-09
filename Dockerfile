# Imagine de bază pentru aplicația Python
FROM python:3.10-slim

ARG KEY = "FUohm9A4TvvCSChSG7"
ARG SECRET = "tJAfR9ddpKCJ3ubOXdBViuprX8R9tU3V6B1v"

ARG TOKEN = '7877883188:AAGdqomhdm9HdOkyybIrHWfw_kXVf9u-9Tc'
ARG CHAT = "6527491132"

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

# Copiază codul aplicației
COPY . /app
WORKDIR /app

# Rulează aplicația
CMD ["python", "script.py"]
