FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies & Chrome + ChromeDriver
RUN apt-get update && apt-get install -y \
    wget curl unzip \
    libnss3 libgdk-pixbuf2.0-0 libatk1.0-0 libatk-bridge2.0-0 \
    libdbus-1-3 libxtst6 libxrandr2 libxss1 \
    libappindicator3-1 libasound2 fonts-liberation \
    libnspr4 libu2f-udev \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && dpkg -i google-chrome-stable_current_amd64.deb || apt-get install -fy \
    && LATEST=$(curl -sSL https://chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -q https://chromedriver.storage.googleapis.com/${LATEST}/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/local/bin/chromedriver \
    && chmod +x /usr/local/bin/chromedriver \
    && rm -rf /var/lib/apt/lists/* google-chrome-stable_current_amd64.deb chromedriver_linux64.zip

WORKDIR /app

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py"]
